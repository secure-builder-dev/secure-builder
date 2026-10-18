import pytest
import datetime
from datetime import timezone

from app.rules import (
    USERS,
    ticket_to_dict,
    create_ticket,
)
from app.models import Ticket

# Helper to compare ISO8601 strings with datetime objects
def isoformat(dt: datetime.datetime) -> str:
    return dt.isoformat()


def test_users_and_ticket_to_dict_structure(db):
    # Ensure USERS is defined correctly
    assert hasattr(__import__('app.rules'), 'USERS')
    assert USERS == ("her", "him")

    # Create a Ticket instance manually
    now = datetime.datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    ticket = Ticket(
        title="Sample",
        details="Details",
        priority="low",
        due=datetime.date(2023, 2, 1),
        status="open",
        filed_by="her",
        assigned_to="him",
        created_at=now,
        updated_at=now,
    )
    # Add to session to get an id
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    d = ticket_to_dict(ticket)
    # Expected keys
    expected_keys = {
        "id",
        "title",
        "details",
        "priority",
        "due",
        "status",
        "filed_by",
        "assigned_to",
        "created_at",
        "updated_at",
    }
    assert set(d.keys()) == expected_keys
    # Check types and formats
    assert isinstance(d["id"], int)
    assert d["title"] == "Sample"
    assert d["details"] == "Details"
    assert d["priority"] == "low"
    assert d["due"] == "2023-02-01"
    assert d["status"] == "open"
    assert d["filed_by"] == "her"
    assert d["assigned_to"] == "him"
    assert d["created_at"] == isoformat(now)
    assert d["updated_at"] == isoformat(now)


def test_create_ticket_invalid_filed_by_and_extra_key(db):
    # Invalid filed_by
    with pytest.raises(ValueError):
        create_ticket(db, "unknown", {"title": "Test"})

    # Extra unexpected key in data
    with pytest.raises(ValueError):
        create_ticket(db, "her", {"title": "Test", "extra": 123})


def test_create_ticket_field_validations(db):
    # Missing title
    with pytest.raises(ValueError):
        create_ticket(db, "her", {})

    # Title not a string
    with pytest.raises(ValueError):
        create_ticket(db, "her", {"title": 123})

    # Title too long after stripping
    long_title = "a" * 121
    with pytest.raises(ValueError):
        create_ticket(db, "her", {"title": long_title})

    # Title empty after stripping
    with pytest.raises(ValueError):
        create_ticket(db, "her", {"title": "   "})

    # Details not a string
    with pytest.raises(ValueError):
        create_ticket(db, "her", {"title": "Ok", "details": 5})

    # Details too long
    long_details = "b" * 1001
    with pytest.raises(ValueError):
        create_ticket(db, "her", {"title": "Ok", "details": long_details})

    # Invalid priority
    with pytest.raises(ValueError):
        create_ticket(db, "her", {"title": "Ok", "priority": "high"})

    # Due not a string nor None
    with pytest.raises(ValueError):
        create_ticket(db, "her", {"title": "Ok", "due": 20230101})

    # Due wrong format
    with pytest.raises(ValueError):
        create_ticket(db, "her", {"title": "Ok", "due": "2023/01/01"})

    # Due non‑existent date
    with pytest.raises(ValueError):
        create_ticket(db, "her", {"title": "Ok", "due": "2023-02-30"})


def test_create_ticket_successful_creation(db):
    # Freeze time for reproducibility
    fixed_now = datetime.datetime(2023, 3, 15, 9, 30, 0, tzinfo=timezone.utc)
    # Monkeypatch datetime to return fixed_now when utcnow() is called inside create_ticket
    class FixedDatetime(datetime.datetime):
        @classmethod
        def utcnow(cls):
            return fixed_now

    # Apply monkeypatch
    original_datetime = datetime.datetime
    datetime.datetime = FixedDatetime
    try:
        data = {
            "title": "  New Ticket  ",
            "details": "Some details",
            "priority": "urgent",
            "due": "2023-04-01",
        }
        ticket_dict = create_ticket(db, "her", data)
    finally:
        # Restore original datetime class
        datetime.datetime = original_datetime

    # Verify returned dict matches ticket_to_dict output
    ticket = db.query(Ticket).filter_by(id=ticket_dict["id"]).one()
    assert ticket.title == "New Ticket"  # stripped
    assert ticket.details == "Some details"
    assert ticket.priority == "urgent"
    assert ticket.due == datetime.date(2023, 4, 1)
    assert ticket.status == "open"
    assert ticket.filed_by == "her"
    assert ticket.assigned_to == "him"  # opposite of filed_by
    # created_at and updated_at should be the fixed time
    assert ticket.created_at == fixed_now
    assert ticket.updated_at == fixed_now
    # Ensure dict representation matches
    assert ticket_dict == ticket_to_dict(ticket)

    # Ensure the ticket was committed (has an id)
    assert ticket.id is not None

    # Ensure created_at and updated_at are equal
    assert ticket.created_at == ticket.updated_at

    # Ensure they are timezone‑aware UTC
    assert ticket.created_at.tzinfo is not None
    assert ticket.created_at.tzinfo.utcoffset(ticket.created_at) == datetime.timedelta(0)

    # Ensure the ticket is persisted in the DB
    fetched = db.get(Ticket, ticket.id)
    assert fetched is not None
    assert fetched.title == "New Ticket"

    # Clean up session for other tests
    db.rollback()

    # Verify that ticket_to_dict formats due and timestamps correctly
    d = ticket_to_dict(fetched)
    assert d["due"] == "2023-04-01"
    assert d["created_at"] == fixed_now.isoformat()
    assert d["updated_at"] == fixed_now.isoformat()

    # Verify that the assigned_to is the other user
    assert fetched.assigned_to == ("him" if fetched.filed_by == "her" else "her")

    # Verify that status is exactly 'open'
    assert fetched.status == "open"

    # Verify that no extra fields were stored beyond those defined in the model
    model_columns = {col.name for col in Ticket.__table__.columns}
    assert set(d.keys()) == model_columns.union({"id"})

    # Verify that the function raises no error for minimal valid input (only title)
    minimal_ticket = create_ticket(db, "him", {"title": "Minimal"})
    assert minimal_ticket["details"] == ""
    assert minimal_ticket["priority"] == "normal"
    assert minimal_ticket["due"] is None
    assert minimal_ticket["filed_by"] == "him"
    assert minimal_ticket["assigned_to"] == "her"
    assert minimal_ticket["status"] == "open"
    # timestamps are present and ISO‑8601 formatted
    datetime.datetime.fromisoformat(minimal_ticket["created_at"])
    datetime.datetime.fromisoformat(minimal_ticket["updated_at"])
    # Ensure created_at and updated_at are equal for this minimal case as well
    assert minimal_ticket["created_at"] == minimal_ticket["updated_at"]

    # Clean up the minimal ticket as well
    db.rollback()
  