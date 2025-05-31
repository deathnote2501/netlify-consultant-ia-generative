import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Text, String, Integer, func, DateTime # Ensure DateTime is imported
from sqlalchemy.dialects.postgresql import UUID as PG_UUID # For UUID type, more explicit for PG
from sqlalchemy.orm import Mapped, mapped_column
from formation_ia_backend.infrastructure.database.session import Base
# from formation_ia_backend.domain.models.user import DbUser # Not strictly needed for model definition unless relationship is defined here

class DbChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    slide_id: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)  # "user" or "ai"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), # Using DateTime(timezone=True)
        server_default=func.now(),
        nullable=False
    )

    # Optional: Define relationship to DbUser if you need to access user object from chat message
    # from sqlalchemy.orm import relationship
    # user: Mapped["DbUser"] = relationship(back_populates="chat_messages") # Requires "chat_messages" on DbUser

    def __repr__(self):
        return f"<DbChatMessage(id={self.id}, user_id={self.user_id}, slide_id={self.slide_id}, role='{self.role}')>"
