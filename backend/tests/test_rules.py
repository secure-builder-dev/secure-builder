import pytest
import os
from datetime import datetime, date, timedelta, timezone
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.db import Base, SessionLocal, init_db
from app.models import Ticket
from app.rules import USERS, create_ticket, change_status, dashboard, filed

@pytest.fixture(scope="function", autouse=True)
def setup_db():
    db_url = os.getenv("TICKETER_DATABASE_URL", "postgresql+psycopg://postgres@127.0.0.1:55432/ticketer")
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)

@pytest.fixture
def session():
    session = SessionLocal()
    yield session
    session.close()

def test_db_config_and_init():
    # Clause 1
    init_db()
    # Verify tables exist by querying
    with SessionLocal() as session:
        result = session.execute(text("SELECT table_name FROM information_schema.tables WHERE table_name = 'tickets'")).fetchone()
        assert result is not None

def test_ticket_model_columns():
    # Clause 2
    ticket = Ticket()
    assert hasattr(ticket, 'id')
    assert hasattr(ticket, 'title')
    assert hasattr(ticket, 'details')
    assert hasattr(ticket, 'priority')
    assert hasattr(ticket, 'due')
    assert hasattr(ticket, 'status')
    assert hasattr(ticket, 'filed_by')
    assert hasattr(ticket, 'assigned_to')
    assert hasattr(ticket, 'created_at')
    assert hasattr(ticket, 'updated_at')

def test_create_ticket_success(session):
    # Clause 3
    data = {
        "title": "  Clean the kitchen  ",
        "details": "Mop the floor",
        "priority": "urgent",
        "due": "2026-01-01"
    }
    ticket_dict = create_ticket(session, "her", data)
    
    assert ticket_dict['title'] == "Clean the kitchen"
    assert ticket_dict['filed_by'] == "her"
    assert ticket_dict['assigned_to'] == "him"
    assert ticket_dict['status'] == "open"
    assert ticket_dict['priority'] == "urgent"
    assert ticket_dict['due'] == "2026-01-01"
    assert "created_at" in ticket_dict
    assert "updated_at" in ticket_dict
    # Check ISO-8601 format
    datetime.fromisoformat(ticket_dict['created_at'])

def test_create_ticket_invalid_inputs(session):
    # Clause 4
    with pytest.raises(ValueError):
        create_ticket(session, "stranger", {"title": "Valid"})
    with pytest.raises(ValueError):
        create_ticket(session, "her", {"details": "No title"})
    with pytest.raises(ValueError):
        create_ticket(session, "her", {"title": " "})
    with pytest.raises(ValueError):
        create_ticket(session, "her", {"title": "a" * 121})
    with pytest.raises(ValueError):
        create_ticket(session, "her", {"title": "Valid", "priority": "extreme"})
    with pytest.raises(ValueError):
        create_ticket(session, "her", {"title": "Valid", "due": "not-a-date"})
    with pytest.raises(ValueError):
        create_ticket(session, "her", {"title": "Valid", "hack": "me"})

def test_change_status_success(session):
    # Clause 5
    t = create_ticket(session, "her", {"title": "Task"})
    
    res = change_status(session, t['id'], "him", "acknowledged")
    assert res['status'] == "acknowledged"
    
    res = change_status(session, t['id'], "him", "in_progress")
    assert res['status'] == "in_progress"
    
    res = change_status(session, t['id'], "him", "done")
    assert res['status'] == "done"
    
    res = change_status(session, t['id'], "her", "closed")
    assert res['status'] == "closed"

def test_change_status_errors(session):
    # Clause 6
    t = create_ticket(session, "her", {"title": "Task"})
    
    with pytest.raises(LookupError):
        change_status(session, 999, "him", "acknowledged")
    
    with pytest.raises(ValueError):
        change_status(session, t['id'], "him", "ghost-status")
    
    with pytest.raises(ValueError):
        change_status(session, t['id'], "him", "done")
    
    with pytest.raises(PermissionError):
        change_status(session, t['id'], "her", "acknowledged")

def test_dashboard_logic(session):
    # Clause 7
    today = date(2026, 1, 10)
    
    t1 = create_ticket(session, "her", {"title": "T1", "priority": "urgent"})
    t2 = create_ticket(session, "her", {"title": "T2", "due": "2026-01-10"})
    t3 = create_ticket(session, "her", {"title": "T3", "due": "2026-01-12"})
    t4 = create_ticket(session, "her", {"title": "T4", "due": "2026-02-01"})
    t5 = create_ticket(session, "her", {"title": "T5"})
    
    # Move T3 to in_progress
    change_status(session, t3['id'], "him", "acknowledged")
    change_status(session, t3['id'], "him", "in_progress")
    
    dash = dashboard(session, "him", today)
    
    assert dash['todo'][0]['title'] == "T1"
    assert dash['todo'][1]['title'] == "T2"
    assert dash['todo'][2]['title'] == "T4"
    assert dash['todo'][3]['title'] == "T5"
    assert dash['in_progress'][0]['title'] == "T3"

def test_dashboard_completed(session):
    # Clause 8
    today = date(2026, 1, 10)
    t6 = create_ticket(session, "her", {"title": "T6"})
    change_status(session, t6['id'], "him", "acknowledged")
    change_status(session, t6['id'], "him", "in_progress")
    change_status(session, t6['id'], "him", "done")
    
    dash = dashboard(session, "him", today)
    assert dash['completed'][0]['title'] == "T6"

def test_filed_tickets(session):
    # Clause 9
    create_ticket(session, "her", {"title": "H1"})
    create_ticket(session, "her", {"title": "H2"})
    create_ticket(session, "him", {"title": "M1"})
    
    her_filed = filed(session, "her")
    assert len(her_filed) == 2
    assert her_filed[0]['title'] == "H2"

def test_timestamp_manipulation(session):
    # Clause 10: Test that we can set timestamps directly on the model
    t = create_ticket(session, "her", {"title": "Time Test"})
    
    # Get the model instance
    from app.models import Ticket
    ticket_obj = session.query(Ticket).filter(Ticket.id == t['id']).one()
    
    past_time = datetime(2020, 1, 1, tzinfo=timezone.utc)
    ticket_obj.created_at = past_time
    session.commit()
    
    # Verify it persists
    updated_t = filed(session, "her")[0]
    assert updated_t['created_at'] == past_time.isoformat()
