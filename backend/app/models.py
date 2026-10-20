from sqlalchemy import Date, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(120))
    details: Mapped[str] = mapped_column(String(1000), default="")
    priority: Mapped[str] = mapped_column(String)
    due: Mapped[object | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String)
    filed_by: Mapped[str] = mapped_column(String)
    assigned_to: Mapped[str] = mapped_column(String)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True))
