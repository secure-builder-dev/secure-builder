import pytest
from datetime import datetime, date, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db import Base
from app.models import Ticket
import os

# Use the environment variable for the database URL
DATABASE_URL = os.getenv("TICKETER_DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

@pytest.fixture(scope="function", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)

from app.household import household_board

def test_household_board_structure(setup_db):
    """Clause 1: Returns correct structure and includes tickets from both users"""
    session = setup_db
    today = date(2026, 1, 10)
    
    t1 = Ticket(title="T1", status="open", filed_by="her", assigned_to="him", 
                created_at=datetime(2026, 1, 1, tzinfo=timezone.utc), 
                updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    t2 = Ticket(title="T2", status="in_progress", filed_by="him", assigned_to="her", 
                created_at=datetime(2026, 1, 2, tzinfo=timezone.utc), 
                updated_at=datetime(2026, 1, 2, tzinfo=timezone.utc))
    session.add_all([t1, t2])
    session.commit()

    result = household_board(session, today)
    assert set(result.keys()) == {"todo", "in_progress", "completed"}
    assert len(result["todo"]) == 1
    assert len(result["in_progress"]) == 1
    assert result["todo"][0]["title"] == "T1"
    assert result["in_progress"][0]["title"] == "T2"

def test_household_board_todo_in_progress_ordering(setup_db):
    """Clause 2: todo (open/acknowledged) and in_progress (in_progress) ordered by oldest created_at first"""
    session = setup_db
    today = date(2026, 1, 10)
    
    # Todo: open and acknowledged
    t1 = Ticket(title="Old Open", status="open", filed_by="her", assigned_to="him", 
                created_at=datetime(2026, 1, 1, tzinfo=timezone.utc), 
                updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    t2 = Ticket(title="New Ack", status="acknowledged", filed_by="her", assigned_to="him", 
                created_at=datetime(2026, 1, 2, tzinfo=timezone.utc), 
                updated_at=datetime(2026, 1, 2, tzinfo=timezone.utc))
    
    # In Progress
    t3 = Ticket(title="Old IP", status="in_progress", filed_by="him", assigned_to="her", 
                created_at=datetime(2026, 1, 1, tzinfo=timezone.utc), 
                updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    t4 = Ticket(title="New IP", status="in_progress", filed_by="him", assigned_to="her", 
                created_at=datetime(2026, 1, 2, tzinfo=timezone.utc), 
                updated_at=datetime(2026, 1, 2, tzinfo=timezone.utc))
    
    session.add_all([t1, t2, t3, t4])
    session.commit()

    result = household_board(session, today)
    assert [t["title"] for t in result["todo"]] == ["Old Open", "New Ack"]
    assert [t["title"] for t in result["in_progress"]] == ["Old IP", "New IP"]

def test_household_board_completed_filtering_and_ordering(setup_db):
    """Clause 3: completed (done/closed) within 7 days ending today, newest updated_at first"""
    session = setup_db
    today = date(2026, 1, 10)
    
    # Within 7 days (Jan 4 to Jan 10)
    t1 = Ticket(title="Old Done", status="done", filed_by="her", assigned_to="him", 
                created_at=datetime(2026, 1, 1, tzinfo=timezone.utc), 
                updated_at=datetime(2026, 1, 4, tzinfo=timezone.utc))
    t2 = Ticket(title="New Closed", status="closed", filed_by="her", assigned_to="him", 
                created_at=datetime(2026, 1, 1, tzinfo=timezone.utc), 
                updated_at=datetime(2026, 1, 9, tzinfo=timezone.utc))
    
    # Outside 7 days (Jan 3)
    t3 = Ticket(title="Too Old", status="done", filed_by="her", assigned_to="him", 
                created_at=datetime(2026, 1, 1, tzinfo=timezone.utc), 
                updated_at=datetime(2026, 1, 3, tzinfo=timezone.utc))
    
    session.add_all([t1, t2, t3])
    session.commit()

    result = household_board(session, today)
    # Should only have t1 and t2, ordered by updated_at DESC
    assert [t["title"] for t in result["completed"]] == ["New Closed", "Old Done"]
    assert any(t["title"] == "Too Old" for t in result["completed"]) is False
