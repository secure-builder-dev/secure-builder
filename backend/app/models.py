from sqlalchemy import Column, Integer, String, Date, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Ticket(Base):
    """Ticket model for the honey-do application."""
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(120))
    details: Mapped[str] = mapped_column(String(1000), default="")
    priority: Mapped[str] = mapped_column(String)
    due: Mapped[Date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String)
    filed_by: Mapped[str] = mapped_column(String)
    assigned_to: Mapped[str] = mapped_column(String)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True))