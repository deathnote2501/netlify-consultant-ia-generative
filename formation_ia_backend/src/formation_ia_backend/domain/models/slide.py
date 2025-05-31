from sqlalchemy import Integer, String, JSON, ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from formation_ia_backend.infrastructure.database.session import Base # Adjusted import path

class DbSlide(Base):
    __tablename__ = "slides"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    order: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    template_type: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[dict] = mapped_column(JSON, nullable=False) # Using dict for JSON content
    specific_prompt: Mapped[str | None] = mapped_column(String, nullable=True)
    suggested_messages: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)

    def __repr__(self):
        return f"<DbSlide(id={self.id}, order={self.order}, template_type='{self.template_type}')>"
