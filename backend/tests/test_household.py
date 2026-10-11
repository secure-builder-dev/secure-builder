import pytest
from datetime import date, datetime, timezone, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os

from app.models import Ticket
from app.db import Base

# The target function we are testing for
from app.household import household_board

DATABASE_URL = os.getenv("TICKETER_DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)

def test_household_board_structure_and_content(setup_db):
    """Clause 1: returns correct structure and tickets for both users"""
    session = setup_db
    today = date(2026, 1, 10)
    
    t1 = Ticket(
        title="Her Ticket", details="", priority="normal", status="open",
        filed_by="her", assigned_to="him",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc)
    )
    t2 = Ticket(
        title="Him Ticket", details="", priority="normal", status="in_progress",
        filed_by="him", assigned_to="her",
        created_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 2, tzinfo=timezone.utc)
    )
    session.add_all([t1, t2])
    session.commit()

    result = household_board(session, today)
    
    assert set(result.keys()) == {"todo", "in_progress", "completed"}
    assert len(result["todo"]) == 1
    assert len(result["in_progress"]) == 1
    assert result["todo"][0]["title"] == "Her Ticket"
    assert result["in_progress"][0]["title"] == "Him Ticket"

def test_household_board_todo_in_progress_ordering(setup_db):
    """Clause 2: todo (open/ack) and in_progress sorted by created_at oldest first"""
    session = setup_db
    today = date(2026, 1, 10)
    
    # Todo: open and acknowledged
    t1 = Ticket(
        title="Old Open", status="open", filed_by="her", assigned_to="him",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc), updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc)
    )
    t2 = Ticket(
        title="New Ack", status="acknowledged", filed_by="him", assigned_to="her",
        created_at=datetime(2026, 1, 2, tzinfo=timezone.utc), updated_at=datetime(2026, 1, 2, tzinfo=timezone.utc)
    )
    # In Progress
    t3 = Ticket(
        title="Old IP", status="in_progress", filed_by="her", assigned_to="him",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc), updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc)
    )
    t4 = Ticket(
        title="New IP", status="in_progress", filed_by="him", assigned_to="her",
        created_at=datetime(2026, 1, 2, tzinfo=timezone.utc), updated_at=datetime(2026, 1, 2, tzinfo=timezone.utc)
    )
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
    t1 = Ticket(
        title="Recent Done", status="done", filed_by="her", assigned_to="him",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 5, tzinfo=timezone.utc)
    )
    t2 = Ticket(
        title="Very Recent Closed", status="closed", filed_by="him", assigned_to="her",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 9, tzinfo=timezone.utc)
    )
    # Too old (before Jan 4)
    t3 = Ticket(
        title="Old Done", status="done", filed_by="her", assigned_to="him",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 3, tzinfo=timezone.utc)
    )
    session.add_all([t1, t2, t3])
    session.commit()

    result = household_board(session, today)
    
    # Should only have t1 and t2, sorted by updated_at DESC
    assert [t["title"] for t in result["completed"]] == ["Very Recent Closed", "Recent Done"]
    assert "Old Done" not in [t["title"] for t in result["completed"]]
