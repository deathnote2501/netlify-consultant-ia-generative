from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel # BaseModel needed for Pydantic v2 if not using fastapi_users' ones directly

from fastapi_users import schemas as fu_schemas # Use an alias for fastapi_users.schemas

class UserRead(fu_schemas.BaseUser[UUID]):
    # Inherits id, email, is_active, is_superuser, is_verified from BaseUser

    # Custom fields from DbUser to be exposed in API responses
    submitted_email: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    active_subscription_id: Optional[str] = None
    subscription_tier: Optional[str] = None
    subscription_expires_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True
    }


class UserCreate(fu_schemas.BaseUserCreate):
    # Inherits email, password.
    # FastAPI Users handles the creation process.
    # Add any extra fields required *at registration time* here.
    pass

class UserUpdate(fu_schemas.BaseUserUpdate):
    # Inherits password, email (optional), is_active (optional),
    # is_superuser (optional), is_verified (optional).
    submitted_email: Optional[str] = None # Example: User might update their "submitted_email"
