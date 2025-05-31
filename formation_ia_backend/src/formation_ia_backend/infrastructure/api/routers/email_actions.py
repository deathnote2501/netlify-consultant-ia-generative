from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr # For request body validation

from formation_ia_backend.infrastructure.database.session import get_async_db
# Correctly import get_user_manager and current_active_user
from formation_ia_backend.application.services.user_service import get_user_manager, current_active_user, UserManager
from formation_ia_backend.application.services.email_verification_service import EmailVerificationService
from formation_ia_backend.infrastructure.email.brevo_adapter import BrevoEmailAdapter
from formation_ia_backend.domain.models.user import DbUser # For type hint of current_user_db_model
from formation_ia_backend.domain.schemas.user import UserRead # For type hint of current_user_schema

router = APIRouter()

class EmailSubmissionRequest(BaseModel):
    email: EmailStr # Validate that the input is an email

@router.post(
    "/submit-for-verification",
    status_code=status.HTTP_202_ACCEPTED
)
async def submit_email_for_slide_verification(
    request_body: EmailSubmissionRequest = Body(...),
    db: AsyncSession = Depends(get_async_db),
    current_user_schema: UserRead = Depends(current_active_user),
    user_manager: UserManager = Depends(get_user_manager)
):
    # Fetch the DbUser model instance using the ID from the UserRead schema
    current_user_db_model: Optional[DbUser] = await user_manager.get(current_user_schema.id)
    if not current_user_db_model:
         # This should ideally not happen if current_active_user guarantees a valid user
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active user not found in database.")

    # Instantiate BrevoEmailAdapter safely
    try:
        brevo_adapter = BrevoEmailAdapter()
    except ValueError as e: # Catch API key errors from BrevoEmailAdapter.__init__
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Email service is currently unavailable: {str(e)}"
        )

    # Instantiate EmailVerificationService with its dependencies
    email_service = EmailVerificationService(user_manager=user_manager, brevo_adapter=brevo_adapter)

    try:
        await email_service.request_slide_email_submission_verification(
            db=db, # Pass the session for this specific operation
            current_user=current_user_db_model,
            email_to_verify=request_body.email
        )
        return {"message": "Verification email requested. Please check your inbox."}
    except HTTPException as he:
        # Re-throw HTTPExceptions raised by the service (e.g., email sending failure)
        raise he
    except Exception as e:
        # Log e for server visibility
        print(f"Unexpected error in /submit-for-verification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while processing your request."
        )

# Note: The endpoint for confirming the email via a token (e.g., /auth/verify?token=...)
# is handled by the FastAPI Users `verify_router` included in main.py.
# Custom logic after successful verification (like clearing `submitted_email` if it was used to change primary email)
# would typically be placed in an `on_after_verify` hook within the custom `UserManager`
# or by overriding the `UserManager.verify` method.
