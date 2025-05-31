import uuid
from typing import Optional, AsyncGenerator

from fastapi import Depends, Request
from fastapi_users import BaseUserManager, UUIDIDMixin, FastAPIUsers
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from formation_ia_backend.domain.models.user import DbUser
from formation_ia_backend.domain.schemas.user import UserRead, UserCreate, UserUpdate # UserUpdate imported
from formation_ia_backend.infrastructure.database.session import get_async_db
# AsyncSessionLocal might be needed if creating sessions outside Depends, but get_async_db is preferred for dependencies.
from formation_ia_backend.core.config import settings
# Import BrevoAdapter for email sending later
# from formation_ia_backend.infrastructure.email.brevo_adapter import BrevoEmailAdapter

class UserManager(UUIDIDMixin, BaseUserManager[DbUser, uuid.UUID]):
    reset_password_token_secret = settings.JWT_SECRET
    verification_token_secret = settings.JWT_SECRET

    async def on_after_register(self, user: DbUser, request: Optional[Request] = None):
        print(f"User {user.id} with email {user.email} has registered.")
        # Example:
        # verification_token = await self.create_verification_token(user) # Generate token
        # verification_link = f"{settings.FRONTEND_URL}/auth/verify-email?token={verification_token}"
        # print(f"Verification link for {user.email}: {verification_link}") # Log for now
        # brevo_adapter = BrevoEmailAdapter()
        # await brevo_adapter.send_verification_email(user.email, "User Name", verification_link)
        # For now, just print. Actual email sending will be added later.
        # We might also want to send a verification email here.
        # Depending on project settings (e.g., if VERIFY_USER_ON_REGISTER is True in FastAPI Users config)

    async def on_after_forgot_password(
        self, user: DbUser, token: str, request: Optional[Request] = None
    ):
        print(f"User {user.id} with email {user.email} has forgotten their password. Reset token: {token}")
        # Send email with reset token link
        # Example:
        # reset_link = f"{settings.FRONTEND_URL}/auth/reset-password?token={token}"
        # print(f"Password reset link for {user.email}: {reset_link}") # Log for now
        # brevo_adapter = BrevoEmailAdapter()
        # await brevo_adapter.send_password_reset_email(user.email, reset_link)

    async def on_after_request_verify(
        self, user: DbUser, token: str, request: Optional[Request] = None
    ):
        print(f"Verification requested for user {user.id} with email {user.email}. Verification token: {token}")
        # Send email with verification link
        # Example:
        # verification_link = f"{settings.FRONTEND_URL}/auth/verify-email?token={token}"
        # print(f"Verification link for {user.email}: {verification_link}") # Log for now
        # brevo_adapter = BrevoEmailAdapter()
        # await brevo_adapter.send_verification_email(user.email, "User Name", verification_link)

# Note: Changed return type hint for get_user_db to be more specific if possible, but SQLAlchemyUserDatabase is fine.
async def get_user_db(session: AsyncSession = Depends(get_async_db)) -> SQLAlchemyUserDatabase[DbUser, uuid.UUID]:
    yield SQLAlchemyUserDatabase(session, DbUser)

async def get_user_manager(user_db: SQLAlchemyUserDatabase[DbUser, uuid.UUID] = Depends(get_user_db)) -> UserManager:
    yield UserManager(user_db)

bearer_transport = BearerTransport(tokenUrl=f"{settings.API_V1_STR}/auth/jwt/login")

def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=settings.JWT_SECRET, lifetime_seconds=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)

auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

# This instance will be used in routers
# Adjusted type hints for FastAPIUsers based on documentation and common practice
fastapi_users_instance = FastAPIUsers[
    DbUser,
    uuid.UUID,  # User ID type
    UserRead,   # UserRead schema
    UserCreate, # UserCreate schema
    UserUpdate  # UserUpdate schema
](
    get_user_manager,
    [auth_backend],
)

# Dependency to get the current active authenticated user
current_active_user = fastapi_users_instance.current_user(active=True)
# Dependency to get the current active verified user (useful for protecting certain endpoints)
current_active_verified_user = fastapi_users_instance.current_user(active=True, verified=True)
# Dependency to get the current superuser
current_superuser = fastapi_users_instance.current_user(active=True, superuser=True)

# Dependency to optionally get the current active user
optional_current_active_user = fastapi_users_instance.current_user(active=True, optional=True)
