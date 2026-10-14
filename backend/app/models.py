from sqlalchemy import Column, ForeignKey, Integer, String, Date, DateTime
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


class Comment(Base):
    """Comment model for ticket comments."""
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_id: Mapped[int] = mapped_column(Integer, ForeignKey("tickets.id"))
    author: Mapped[str] = mapped_column(String)
    body: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True))


class TicketEvent(Base):
    """TicketEvent model for ticket history events."""
    __tablename__ = "ticket_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_id: Mapped[int] = mapped_column(Integer, ForeignKey("tickets.id"))
    actor: Mapped[str] = mapped_column(String)
    kind: Mapped[str] = mapped_column(String)
    from_status: Mapped[str | None] = mapped_column(String, nullable=True)
    to_status: Mapped[str | None] = mapped_column(String, nullable=True)
    at: Mapped[DateTime] = mapped_column(DateTime(timezone=True))