from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
import logging
from typing import Optional

from formation_ia_backend.application.services.user_service import UserManager
from formation_ia_backend.infrastructure.email.brevo_adapter import BrevoEmailAdapter
from formation_ia_backend.domain.models.user import DbUser
from formation_ia_backend.core.config import settings

logger = logging.getLogger(__name__)

class EmailVerificationService:
    def __init__(self, user_manager: UserManager, brevo_adapter: BrevoEmailAdapter):
        self.user_manager = user_manager
        self.brevo_adapter = brevo_adapter

    async def request_slide_email_submission_verification(
        self,
        db: AsyncSession,
        current_user: DbUser, # Expecting the DbUser model instance
        email_to_verify: str
    ) -> None:
        original_email = current_user.email
        original_is_verified = current_user.is_verified
        original_submitted_email = current_user.submitted_email # Keep track if we need to revert

        # Store the email they typed on the slide
        current_user.submitted_email = email_to_verify

        if current_user.email == email_to_verify and current_user.is_verified:
            logger.info(f"Email {email_to_verify} is already the primary verified email for user {current_user.id}.")
            # Ensure submitted_email is saved if it wasn't already set to this value
            if original_submitted_email != email_to_verify:
                db.add(current_user)
                await db.commit()
                await db.refresh(current_user)
            return

        # If the email to verify is different from current primary, or current primary is not verified:
        if current_user.email != email_to_verify:
            current_user.email = email_to_verify # Set new email as primary
            current_user.is_verified = False    # Mark as unverified since it's a new email
        elif not current_user.is_verified:
            # Email is the same as current_user.email, but it's not verified.
            # is_verified is already False. No change to email or is_verified needed here.
            pass

        db.add(current_user) # Add changes to session (new email, is_verified=False, submitted_email)

        try:
            # UserManager.request_verify_token typically handles setting is_verified=False and saving the user
            # if it's part of its internal logic. We've already set it, which is fine.
            # It will generate a token for `current_user.email` (which is now `email_to_verify`).
            token = await self.user_manager.request_verify_token(current_user, request=None) # request=None is typical for backend-initiated flows

            verification_link = f"{settings.FRONTEND_URL}/auth/verify-email?token={token}" # Adjusted to a more common verify path

            # Use current_user.email (which is now email_to_verify) for user_name placeholder if actual name not available
            user_name_for_email = current_user.email

            email_sent = await self.brevo_adapter.send_verification_email(
                to_email=email_to_verify,
                user_name=user_name_for_email,
                verification_link=verification_link
            )

            if not email_sent:
                logger.error(f"Failed to send verification email to {email_to_verify} for user {current_user.id}")
                await db.rollback()
                # Revert in-memory object state to avoid confusion if object is reused
                current_user.email = original_email
                current_user.is_verified = original_is_verified
                current_user.submitted_email = original_submitted_email
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to send verification email.")

            # If email sending was successful, commit the changes to user (new email, is_verified=False, submitted_email)
            await db.commit()
            await db.refresh(current_user)
            logger.info(f"Verification email sent to {email_to_verify} for user {current_user.id}.")

        except Exception as e:
            await db.rollback()
            # Revert in-memory changes as well
            current_user.email = original_email
            current_user.is_verified = original_is_verified
            current_user.submitted_email = original_submitted_email
            logger.error(f"Error in request_slide_email_submission_verification for user {current_user.id}, email {email_to_verify}: {e}", exc_info=True)
            # Avoid exposing raw error messages if possible
            if isinstance(e, HTTPException): # Re-raise if it's already an HTTPException
                raise
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An error occurred while requesting email verification.")


    async def confirm_slide_email_submission(
        self,
        token: str
        # db: AsyncSession, # db session is implicitly handled by user_manager through get_user_db dependency
    ) -> DbUser: # Return DbUser on success
        try:
            # user_manager.verify should handle finding user by token, setting is_verified=True, and saving.
            # It uses the UserDB instance, which in turn uses a session obtained from get_async_db.
            verified_user: Optional[DbUser] = await self.user_manager.verify(token, request=None)

            if not verified_user:
                # This case might occur if the token is valid but for some reason user object isn't returned (highly unlikely with FastAPI Users)
                # or if the user was deleted between token generation and verification.
                logger.error(f"Token verification did not return a user object for token (or token was invalid but did not raise): {token}")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired verification token, or user not found.")

            logger.info(f"Email {verified_user.email} successfully verified for user {verified_user.id} via slide submission flow.")

            # Optional: Clear submitted_email if it matches the now-verified primary email.
            # This assumes submitted_email was used to change the primary email.
            if verified_user.submitted_email == verified_user.email:
                 verified_user.submitted_email = None
                 # Need a DB session to commit this change.
                 # This highlights that user_manager.verify might not return the session it used.
                 # For simplicity, this step might be omitted or handled in a subsequent user profile update.
                 # Or, the UserManager could be enhanced to run this within its transaction.
                 # For now, let's assume this is not critical for this subtask.
                 # If we need to commit this, we'd need to pass 'db' or get a session here.
                 pass


            return verified_user

        except HTTPException: # Re-raise HTTPExceptions directly
            raise
        except Exception as e: # Catch specific exceptions from FastAPI Users like UserAlreadyVerified, InvalidVerifyToken, UserNotExists
            logger.error(f"Error during email confirmation (slide submission flow) for token {token}: {e}", exc_info=True)
            detail_message = "An error occurred during email confirmation."
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

            # Map known FastAPI Users exception messages to specific HTTP errors
            if "Invalid verify token" in str(e) or "TOKEN_INVALID" in str(e):
                detail_message = "Invalid or expired verification token."
                status_code = status.HTTP_400_BAD_REQUEST
            elif "User already verified" in str(e) or "USER_ALREADY_VERIFIED" in str(e):
                detail_message = "Email is already verified."
                status_code = status.HTTP_400_BAD_REQUEST
            elif "User does not exist" in str(e) or "USER_DOES_NOT_EXIST" in str(e):
                detail_message = "User not found for this token."
                status_code = status.HTTP_404_NOT_FOUND

            raise HTTPException(status_code=status_code, detail=detail_message) from e
