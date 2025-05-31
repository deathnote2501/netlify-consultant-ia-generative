import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, func # Import func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID # For UUID type
from sqlalchemy.orm import Mapped, mapped_column
from formation_ia_backend.infrastructure.database.session import Base

class DbSubscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(String, primary_key=True) # Stripe Subscription ID (e.g., "sub_xxx")
    user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    stripe_customer_id: Mapped[str] = mapped_column(String, nullable=False, index=True)

    plan_id: Mapped[str] = mapped_column(String, nullable=False) # Stripe Price ID (e.g., "price_xxx")
    status: Mapped[str] = mapped_column(String, nullable=False) # e.g., "active", "canceled", "past_due"

    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Optional: Define relationship to DbUser if you need to access user object from subscription
    # from sqlalchemy.orm import relationship
    # user: Mapped["DbUser"] = relationship() # Add back_populates on DbUser if defined there

    def __repr__(self):
        return f"<DbSubscription(id='{self.id}', user_id='{self.user_id}', status='{self.status}')>"
