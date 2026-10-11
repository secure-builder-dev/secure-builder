from sqlalchemy import Column, Integer, String, Text, Date, DateTime, Enum
from sqlalchemy.sql import func
from app.db import Base

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True)
    title = Column(String(120), nullable=False)
    details = Column(Text, default="")
    priority = Column(Enum("low", "normal", "urgent", name="priority_enum"), default="normal")
    due = Column(Date)
    status = Column(String(50), nullable=False)
    filed_by = Column(String(10), nullable=False)
    assigned_to = Column(String(10), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())