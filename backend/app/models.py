from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey
from app.db import Base

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True)
    title = Column(String(120), nullable=False)
    details = Column(String(1000), nullable=True, default="")
    priority = Column(String, nullable=False)
    due = Column(Date, nullable=True)
    status = Column(String, nullable=False)
    filed_by = Column(String, nullable=False)
    assigned_to = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey('tickets.id'), nullable=False)
    author = Column(String, nullable=False)
    body = Column(String(500), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)


class TicketEvent(Base):
    __tablename__ = "ticket_events"

    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey('tickets.id'), nullable=False)
    actor = Column(String, nullable=False)
    kind = Column(String, nullable=False)
    from_status = Column(String, nullable=True)
    to_status = Column(String, nullable=True)
    at = Column(DateTime(timezone=True), nullable=False)
