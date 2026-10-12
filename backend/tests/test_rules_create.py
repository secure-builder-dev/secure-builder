"""GD-1b: USERS, create_ticket and ticket_to_dict."""
import datetime as dt

import pytest

from app.rules import USERS, create_ticket, ticket_to_dict

KEYS = {"id", "title", "details", "priority", "due", "status", "filed_by", "assigned_to", "created_at", "updated_at"}


def test_users():
    assert USERS == ("her", "him")


def test_create_ticket_with_every_field(db):
    t = create_ticket(db, "her", {"title": "Fix the sink", "details": "It drips", "priority": "urgent", "due": "2026-10-20"})
    assert set(t) == KEYS
    assert isinstance(t["id"], int)
    assert t["title"] == "Fix the sink"
    assert t["details"] == "It drips"
    assert t["priority"] == "urgent"
    assert t["due"] == "2026-10-20"
    assert t["status"] == "open"
    assert t["filed_by"] == "her"
    assert t["assigned_to"] == "him"


def test_create_ticket_assigns_to_the_other_user(db):
    assert create_ticket(db, "him", {"title": "Walk the dog"})["assigned_to"] == "her"
    assert create_ticket(db, "her", {"title": "Mow"})["assigned_to"] == "him"


def test_create_ticket_defaults(db):
    t = create_ticket(db, "him", {"title": "Groceries"})
    assert t["details"] == ""
    assert t["priority"] == "normal"
    assert t["due"] is None


def test_create_ticket_strips_the_title(db):
    assert create_ticket(db, "her", {"title": "  Paint  "})["title"] == "Paint"


def test_create_ticket_timestamps_are_utc_iso_strings_and_equal(db):
    before = dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=5)
    t = create_ticket(db, "her", {"title": "T"})
    created = dt.datetime.fromisoformat(t["created_at"])
    updated = dt.datetime.fromisoformat(t["updated_at"])
    assert created.tzinfo is not None and created.utcoffset() == dt.timedelta(0)
    assert before <= created <= dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=5)
    assert created == updated


def test_create_ticket_is_committed(db):
    from app.db import SessionLocal
    from app.models import Ticket
    t = create_ticket(db, "her", {"title": "Stored"})
    other = SessionLocal()
    try:
        assert other.get(Ticket, t["id"]).title == "Stored"
    finally:
        other.close()


def test_title_length_limits(db):
    assert create_ticket(db, "her", {"title": "a" * 120})["title"] == "a" * 120
    assert create_ticket(db, "her", {"title": "a"})["title"] == "a"
    with pytest.raises(ValueError):
        create_ticket(db, "her", {"title": "a" * 121})


@pytest.mark.parametrize("data", [
    {},
    {"title": ""},
    {"title": "   "},
    {"title": 5},
    {"title": None},
])
def test_missing_or_invalid_title_raises(db, data):
    with pytest.raises(ValueError):
        create_ticket(db, "her", data)


@pytest.mark.parametrize("data", [
    {"title": "T", "details": "x" * 1001},
    {"title": "T", "details": 7},
    {"title": "T", "priority": "high"},
    {"title": "T", "priority": None},
    {"title": "T", "due": "not-a-date"},
    {"title": "T", "due": "2026-02-30"},
    {"title": "T", "due": "2026/10/05"},
    {"title": "T", "due": 20261005},
    {"title": "T", "status": "done"},
    {"title": "T", "filed_by": "him"},
])
def test_invalid_field_or_unknown_key_raises(db, data):
    with pytest.raises(ValueError):
        create_ticket(db, "her", data)


def test_details_of_1000_characters_is_allowed(db):
    assert len(create_ticket(db, "her", {"title": "T", "details": "x" * 1000})["details"]) == 1000


@pytest.mark.parametrize("who", ["stranger", "", None, "Her"])
def test_unknown_filer_raises(db, who):
    with pytest.raises(ValueError):
        create_ticket(db, who, {"title": "T"})


def test_a_raising_call_stores_nothing(db):
    from app.models import Ticket
    with pytest.raises(ValueError):
        create_ticket(db, "her", {"title": "T", "priority": "high"})
    assert db.query(Ticket).count() == 0


def test_ticket_to_dict_formats_due_and_timestamps(db):
    from app.models import Ticket
    now = dt.datetime(2026, 10, 1, 9, 30, tzinfo=dt.timezone.utc)
    m = Ticket(title="X", details="d", priority="low", due=dt.date(2026, 10, 3), status="open", filed_by="him",
               assigned_to="her", created_at=now, updated_at=now)
    db.add(m)
    db.commit()
    d = ticket_to_dict(m)
    assert set(d) == KEYS
    assert d["due"] == "2026-10-03"
    assert dt.datetime.fromisoformat(d["created_at"]) == now
    m.due = None
    assert ticket_to_dict(m)["due"] is None


def test_due_none_is_allowed(db):
    assert create_ticket(db, "her", {"title": "T", "due": None, "details": "", "priority": "low"})["due"] is None
