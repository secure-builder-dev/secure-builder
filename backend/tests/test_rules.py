import pytest
import os
import importlib
import sys
from datetime import datetime, date, timedelta, timezone
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# We import these from app, but they don't exist yet
try:
    from app.db import Base, SessionLocal, init_db
    from app.models import Ticket
    from app.rules import USERS, create_ticket, change_status, dashboard, filed
except ImportError:
    Base = None
    SessionLocal = None
    init_db = None
    Ticket = None
    USERS = None
    create_ticket = None
    change_status = None
    dashboard = None
    filed = None

@pytest.fixture(scope="function", autouse=True)
def db_setup():
    url = os.environ.get("TICKETER_DATABASE_URL")
    if not url:
        pytest.skip("TICKETER_DATABASE_URL not set")

    if init_db:
        init_db()

    session = None
    if SessionLocal:
        session = SessionLocal()

    yield session

    if session:
        session.close()

    engine = create_engine(url)
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS tickets"))
        conn.commit()

def test_db_url_requirement():
    # Clause 1: RuntimeError when TICKETER_DATABASE_URL is unset or empty
    original_url = os.environ.get("TICKETER_DATABASE_URL")
    if "app.db" in sys.modules:
        del sys.modules["app.db"]

    try:
        os.environ["TICKETER_DATABASE_URL"] = ""
        import app.db
        importlib.reload(app.db)
        pytest.fail("Should have raised RuntimeError for empty TICKETER_DATABASE_URL")
    except RuntimeError:
        pass
    except Exception as e:
        pytest.fail(f"Expected RuntimeError, got {type(e).__name__}: {e}")
    finally:
        if original_url:
            os.environ["TICKETER_DATABASE_URL"] = original_url
        else:
            os.environ.pop("TICKETER_DATABASE_URL", None)

def test_ticket_model_columns():
    # Clause 2: Check Ticket model columns
    assert Ticket is not None
    cols = Ticket.__table__.columns.keys()
    expected = {
        "id", "title", "details", "priority", "due",
        "status", "filed_by", "assigned_to", "created_at", "updated_at"
    }
    assert expected.issubset(set(cols))

def test_create_ticket_success():
    # Clause 3: Success case for create_ticket
    session = SessionLocal()
    data = {"title": " Fix the sink ", "priority": "urgent", "due": "2026-01-01"}
    ticket = create_ticket(session, "her", data)

    assert ticket["title"] == "Fix the sink"
    assert ticket["assigned_to"] == "him"
    assert ticket["status"] == "open"
    assert "created_at" in ticket
    assert ticket["due"] == "2026-01-01"
    assert "updated_at" in ticket

def test_create_ticket_invalid_inputs():
    # Clause 4: Rejection cases for create_ticket
    session = SessionLocal()

    # Invalid user
    with pytest.raises(ValueError):
        create_ticket(session, "stranger", {"title": "Valid"})

    # Missing title
    with pytest.raises(ValueError):
        create_ticket(session, "her", {"details": "No title"})

    # Title too short/long
    with pytest.raises(ValueError):
        create_ticket(session, "her", {"title": " "})
    with pytest.raises(ValueError):
        create_ticket(session, "her", {"title": "a" * 121})

    # Invalid priority
    with pytest.raises(ValueError):
        create_ticket(session, "her", {"title": "Valid", "priority": "extreme"})

    # Invalid date
    with pytest.raises(ValueError):
        create_ticket(session, "her", {"title": "Valid", "due": "not-a-date"})

    # Extra keys
    with pytest.raises(ValueError):
        create_ticket(session, "her", {"title": "Valid", "hack": "true"})

def test_change_status_success():
    # Clause 5: Valid status moves
    session = SessionLocal()
    t = create_ticket(session, "her", {"title": "Task 1"})

    # open -> acknowledged (assignee)
    updated = change_status(session, t["id"], "him", "acknowledged")
    assert updated["status"] == "acknowledged"

def test_change_status_errors():
    # Clause 6: LookupError, ValueError, PermissionError
    session = SessionLocal()
    t = create_ticket(session, "her", {"title": "Task 1"})

    # LookupError: non-existent
    with pytest.raises(LookupError):
        change_status(session, 999, "him", "acknowledged")

    # LookupError: not a party
    with pytest.raises(LookupError):
        change_status(session, t["id"], "stranger", "acknowledged")

    # ValueError: unknown status
    with pytest.raises(ValueError):
        change_status(session, t["id"], "him", "ghost-status")

    # PermissionError: wrong party (filer cannot move open -> acknowledged)
    with pytest.raises(PermissionError):
        change_status(session, t["id"], "her", "acknowledged")

def test_dashboard_logic():
    # Clause 7 & 8: Dashboard grouping and filtering
    session = SessionLocal()
    today = date(2026, 1, 1)

    # Ticket 1: Urgent (Group 0)
    create_ticket(session, "her", {"title": "T1", "priority": "urgent", "due": "2026-01-05"})
    # Ticket 2: Due today (Group 1)
    create_ticket(session, "her", {"title": "T2", "due": "2026-01-01"})
    # Ticket 3: Due later (Group 2)
    create_ticket(session, "her", {"title": "T3", "due": "2026-01-10"})

    dash = dashboard(session, "him", today)

    assert len(dash["todo"]) == 3
    assert dash["todo"][0]["title"] == "T1" # Group 0
    assert dash["todo"][1]["title"] == "T2" # Group 1
    assert dash["todo"][2]["title"] == "T3" # Group 2

def test_dashboard_completed():
    # Clause 8: Completed tickets filtering and ordering
    session = SessionLocal()
    today = date(2026, 1, 1)

    # Ticket in range
    t1 = create_ticket(session, "her", {"title": "C1"})
    # Ticket out of range (older than 7 days)
    t2 = create_ticket(session, "her", {"title": "C2"})

    # Manually set updated_at for t2 to be 10 days ago
    from app.models import Ticket
    ticket_obj = session.query(Ticket).filter_by(title="C2").first()
    ticket_obj.updated_at = datetime(2025, 12, 20, tzinfo=timezone.utc)
    session.commit()

    # Move both to 'done'
    change_status(session, t1["id"], "him", "acknowledged")
    change_status(session, t1["id"], "him", "in_progress")
    change_status(session, t1["id"], "him", "done")

    change_status(session, t2["id"], "him", "acknowledged")
    change_status(session, t2["id"], "him", "in_progress")
    change_status(session, t2["id"], "him", "done")

    # Re-apply the old date to t2 because change_status updates updated_at to now
    ticket_obj_t2 = session.query(Ticket).filter_by(title="C2").first()
    ticket_obj_t2.updated_at = datetime(2025, 12, 20, tzinfo=timezone.utc)
    session.commit()

    dash = dashboard(session, "him", today)
    assert len(dash["completed"]) == 1
    assert dash["completed"][0]["title"] == "C1"

def test_filed_tickets():
    # Clause 9: filed() returns tickets user filed
    session = SessionLocal()
    create_ticket(session, "her", {"title": "H1"})
    create_ticket(session, "her", {"title": "H2"})
    create_ticket(session, "him", {"title": "M1"})

    her_filed = filed(session, "her")
    assert len(her_filed) == 2
    assert her_filed[0]["title"] == "H2" # Newest first

def test_setup_teardown_behavior():
    # Clause 10: Verify that tables are created and dropped
    # This is implicitly tested by the other tests using the db_setup fixture,
    # but we can check if the table exists during a test.
    session = SessionLocal()
    from sqlalchemy import inspect
    inspector = inspect(session.get_bind())
    assert "tickets" in inspector.get_table_names()
