from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey
from sqlalchemy.sql import func
from .db import Base

class Ticket(Base):
    __tablename__ = 'tickets'
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(120), nullable=False)
    details = Column(Text, default='')
    priority = Column(String(20), default='normal')
    due = Column(Date, nullable=True)
    status = Column(String(20), default='open')
    filed_by = Column(String(20), nullable=False)
    assigned_to = Column(String(20), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)