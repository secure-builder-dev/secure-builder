import pytest
from datetime import datetime, date, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

from app.db import Base
from app.models import Ticket
from app.rules import create_ticket, change_status

# The target function to test
try:
    from app.household import household_board
except ImportError:
    def household_board(*args, **kwargs):
        raise ImportError("backend/app/household.py not yet implemented")

DATABASE_URL = os.getenv("TICKETER_DATABASE_URL")
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)

def test_household_board_structure(setup_db):
    """Clause 1: Returns correct structure and includes tickets from both users"""
    session = setup_db
    today = date(2026, 1, 10)
    
    # Create tickets for both users
    create_ticket(session, "her", {"title": "T1"})
    create_ticket(session, "him", {"title": "T2"})
    
    result = household_board(session, today)
    
    assert set(result.keys()) == {"todo", "in_progress", "completed"}
    # Both should be in todo by default
    assert len(result["todo"]) == 2
    # Verify dict keys match ticket_to_dict (as per design/rules)
    t = result["todo"][0]
    assert set(t.keys()) == {"id", "title", "details", "priority", "due", "status", "filed_by", "assigned_to", "created_at", "updated_at"}

def test_household_board_todo_in_progress_ordering(setup_db):
    """Clause 2: todo (open/acknowledged) and in_progress (in_progress) ordered by oldest created_at first"""
    session = setup_db
    today = date(2026, 1, 10)
    
    # T1: oldest, open
    t1 = Ticket(title="T1", status="open", filed_by="her", assigned_to="him", 
                created_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    # T2: newer, acknowledged
    t2 = Ticket(title="T2", status="acknowledged", filed_by="him", assigned_to="her", 
                created_at=datetime(2026, 1, 2, tzinfo=timezone.utc))
    # T3: oldest, in_progress
    t3 = Ticket(title="T3", status="in_progress", filed_by="her", assigned_to="him", 
                created_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    # T4: newer, in_progress
    t4 = Ticket(title="T4", status="in_progress", filed_by="him", assigned_to="her", 
                created_at=datetime(2026, 1, 2, tzinfo=timezone.utc))
    
    session.add_all([t1, t2, t3, t4])
    session.commit()
    
    result = household_board(session, today)
    
    assert [t["title"] for t in result["todo"]] == ["T1", "T2"]
    assert [t["title"] for t in result["in_progress"]] == ["T3", "T4"]

def test_household_board_completed_filtering_and_ordering(setup_db):
    """Clause 3: completed (done/closed) within 7 days ending today, newest updated_at first"""
    session = setup_db
    today = date(2026, 1, 10)
    
    # T1: done, updated 2 days ago (should be included)
    t1 = Ticket(title="T1", status="done", filed_by="her", assigned_to="him", 
                updated_at=datetime(2026, 1, 8, tzinfo=timezone.utc))
    # T2: closed, updated 1 day ago (should be included, newest)
    t2 = Ticket(title="T2", status="closed", filed_by="him", assigned_to="her", 
                updated_at=datetime(2026, 1, 9, tzinfo=timezone.utc))
    # T3: done, updated 8 days ago (should be excluded)
    t3 = Ticket(title="T3", status="done", filed_by="her", assigned_to="him", 
                updated_at=datetime(2026, 1, 2, tzinfo=timezone.utc))
    
    session.add_all([t1, t2, t3])
    session.commit()
    
    result = household_board(session, today)
    
    # Only T1 and T2, T2 first because it's newer
    assert [t["title"] for t in result["completed"]] == ["T2", "T1"]

def test_household_board_db_lifecycle(setup_db):
    """Clause 4: Verify DB usage and direct timestamp setting"""
    session = setup_db
    today = date(2026, 1, 10)
    
    # This test specifically exercises setting timestamps directly on the model
    # and ensuring the function reads from the DB session provided
    t1 = Ticket(
        title="LifeCycle", 
        status="open", 
        filed_by="her", 
        assigned_to="him", 
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc)
    )
    session.add(t1)
    session.commit()
    
    result = household_board(session, today)
    assert len(result["todo"]) == 1
    assert result["todo"][0]["title"] == "LifeCycle"