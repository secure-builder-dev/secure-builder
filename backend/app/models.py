from datetime import datetime, timezone
from sqlalchemy import Column, Date, DateTime, Integer, String
from app.db import Base

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True)
    title = Column(String(120), nullable=False)
    details = Column(String(1000), default="")
    priority = Column(String(20), default="normal")
    due = Column(Date, nullable=True)
    status = Column(String(20), nullable=False)
    filed_by = Column(String(20), nullable=False)
    assigned_to = Column(String(20), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)
