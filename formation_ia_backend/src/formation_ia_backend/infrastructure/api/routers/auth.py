from fastapi import APIRouter

from formation_ia_backend.application.services.user_service import (
    auth_backend,
    fastapi_users_instance # Using the instance name from user_service.py
)
from formation_ia_backend.domain.schemas.user import UserRead, UserCreate, UserUpdate
# from formation_ia_backend.core.config import settings # Not strictly needed here if prefixes are managed in main.py

# Router for authentication (login, logout, etc.)
auth_router = APIRouter()
auth_router.include_router(
    fastapi_users_instance.get_auth_router(auth_backend),
    prefix="/jwt", # Standard prefix for JWT login/logout within an /auth group
    tags=["Auth"]
)

# Router for registration
register_router = APIRouter()
register_router.include_router(
    fastapi_users_instance.get_register_router(UserRead, UserCreate),
    tags=["Auth"] # Typically, registration is also part of "Auth"
)

# Router for email verification
verify_router = APIRouter()
verify_router.include_router(
    fastapi_users_instance.get_verify_router(UserRead),
    tags=["Auth"] # Verification processes are part of "Auth"
)

# Router for password reset
reset_password_router = APIRouter()
reset_password_router.include_router(
    fastapi_users_instance.get_reset_password_router(),
    tags=["Auth"] # Password reset is part of "Auth"
)

# Router for managing users (GET current user, PATCH current user, GET user by ID (admin))
# This provides endpoints like /me, /{id}
users_management_router = APIRouter() # Renamed to avoid conflict if all are mounted under /users
users_management_router.include_router(
    fastapi_users_instance.get_users_router(UserRead, UserUpdate),
    tags=["Users"] # Separate tag for user management distinct from pure auth operations
)

# Note: These routers will typically be included in main.py, often grouped.
# For example, auth_router, register_router, verify_router, reset_password_router
# might all be prefixed with /auth in main.py.
# The users_management_router might be prefixed with /users in main.py.
