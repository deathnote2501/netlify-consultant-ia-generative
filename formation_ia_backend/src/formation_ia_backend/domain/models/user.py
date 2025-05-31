from typing import Optional
from uuid import UUID
from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean, DateTime # Ensure DateTime is imported
from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTableUUID

from formation_ia_backend.infrastructure.database.session import Base

class DbUser(SQLAlchemyBaseUserTableUUID, Base):
    __tablename__ = "users"

    # Columns from SQLAlchemyBaseUserTableUUID are:
    # id: Mapped[UUID]
    # email: Mapped[str]
    # hashed_password: Mapped[str]
    # is_active: Mapped[bool]
    # is_superuser: Mapped[bool]
    # is_verified: Mapped[bool]  <-- This field will be used for email verification status

    # Additional custom fields:
    submitted_email: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    active_subscription_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    subscription_tier: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    subscription_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True) # Use DateTime for timestamp

    def __repr__(self):
        return f"<DbUser(id={self.id}, email='{self.email}', is_verified={self.is_verified})>"
