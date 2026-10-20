"""TO-4a: rules.edit_ticket and rules.NotEditable."""
import datetime as dt

import pytest

from app import rules
from app.models import Ticket, TicketEvent
from app.rules import create_ticket, edit_ticket, ticket_to_dict
from tests.conftest import at, set_times

OLD = at("2026-01-01")


def _ticket(db, status="open"):
    t = create_ticket(db, "her", {"title": "Paint", "details": "fence", "priority": "low", "due": "2026-11-01"})
    set_times(db, t["id"], created=OLD, updated=OLD, status=status)     # filer her, assignee him
    return t["id"]


def _events(session, tid):
    rows = session.query(TicketEvent).filter(TicketEvent.ticket_id == tid).order_by(TicketEvent.id).all()
    return [(e.kind, e.actor, e.from_status, e.to_status) for e in rows]


def _assert_unchanged(db, tid, before, events_before):
    db.commit()                                   # anything the failed call left pending would be stored now
    db.expire_all()
    assert ticket_to_dict(db.get(Ticket, tid)) == before
    assert _events(db, tid) == events_before


def test_not_editable_is_its_own_exception():
    assert issubclass(rules.NotEditable, Exception)
    assert not issubclass(rules.NotEditable, ValueError)
    assert not issubclass(rules.NotEditable, PermissionError)
    assert not issubclass(rules.NotEditable, LookupError)


def test_edit_every_field(db):
    tid = _ticket(db)
    t = edit_ticket(db, tid, "her", {"title": "  Paint the shed  ", "details": "", "priority": "urgent",
                                     "due": "2026-12-24"})
    assert (t["title"], t["details"], t["priority"], t["due"]) == ("Paint the shed", "", "urgent", "2026-12-24")
    assert (t["status"], t["filed_by"], t["assigned_to"]) == ("open", "her", "him")
    db.expire_all()
    assert t == ticket_to_dict(db.get(Ticket, tid))


@pytest.mark.parametrize("data,changed", [
    ({"title": "New"}, {"title": "New"}),
    ({"details": "shed too"}, {"details": "shed too"}),
    ({"priority": "normal"}, {"priority": "normal"}),
    ({"due": "2026-11-30"}, {"due": "2026-11-30"}),
    ({"due": None}, {"due": None}),
])
def test_edit_changes_only_the_given_fields_and_sets_updated_at(db, data, changed):
    tid = _ticket(db)
    before = ticket_to_dict(db.get(Ticket, tid))
    t = edit_ticket(db, tid, "her", data)
    updated = dt.datetime.fromisoformat(t.pop("updated_at"))
    assert updated > OLD
    assert dt.datetime.now(dt.timezone.utc) - updated < dt.timedelta(minutes=1)
    expected = {k: v for k, v in before.items() if k != "updated_at"}
    expected.update(changed)
    assert t == expected


@pytest.mark.parametrize("status", ["open", "acknowledged"])
def test_edit_records_an_edited_event_and_commits(db, status):
    from app.db import SessionLocal
    tid = _ticket(db, status)
    edit_ticket(db, tid, "her", {"title": "Stored"})
    other = SessionLocal()
    try:
        assert other.get(Ticket, tid).title == "Stored"
        assert other.get(Ticket, tid).status == status
        assert _events(other, tid)[-1] == ("edited", "her", None, None)
        assert [k for k, *_ in _events(other, tid)].count("edited") == 1
    finally:
        other.close()


@pytest.mark.parametrize("tid_offset,user", [(1000, "her"), (0, "stranger"), (0, None)])
def test_missing_ticket_or_non_party_raises_lookup_error(db, tid_offset, user):
    tid = _ticket(db)
    before, events = ticket_to_dict(db.get(Ticket, tid)), _events(db, tid)
    with pytest.raises(LookupError):
        edit_ticket(db, tid + tid_offset, user, {"title": "X"})
    _assert_unchanged(db, tid, before, events)


@pytest.mark.parametrize("data", [
    None, [], "title", [("title", "X")],
    {},
    {"status": "done"}, {"title": "X", "filed_by": "him"}, {"assigned_to": "her"},
    {"title": ""}, {"title": "   "}, {"title": "a" * 121}, {"title": 5}, {"title": None},
    {"details": "x" * 1001}, {"details": 7},
    {"priority": "high"}, {"priority": None},
    {"due": "not-a-date"}, {"due": "2026-02-30"}, {"due": "2026/10/05"}, {"due": 20261005},
    {"title": "Fine", "priority": "high"},
])
def test_invalid_data_raises_value_error_and_changes_nothing(db, data):
    tid = _ticket(db)
    before, events = ticket_to_dict(db.get(Ticket, tid)), _events(db, tid)
    with pytest.raises(ValueError):
        edit_ticket(db, tid, "her", data)
    _assert_unchanged(db, tid, before, events)


def test_the_assignee_raises_permission_error(db):
    tid = _ticket(db)
    before, events = ticket_to_dict(db.get(Ticket, tid)), _events(db, tid)
    with pytest.raises(PermissionError):
        edit_ticket(db, tid, "him", {"title": "Mine now"})
    _assert_unchanged(db, tid, before, events)


@pytest.mark.parametrize("status", ["in_progress", "done", "closed"])
def test_past_acknowledged_raises_not_editable(db, status):
    tid = _ticket(db, status)
    before, events = ticket_to_dict(db.get(Ticket, tid)), _events(db, tid)
    with pytest.raises(rules.NotEditable):
        edit_ticket(db, tid, "her", {"title": "Late"})
    _assert_unchanged(db, tid, before, events)


def test_lookup_error_comes_before_value_error(db):
    tid = _ticket(db)
    with pytest.raises(LookupError):
        edit_ticket(db, tid, "stranger", {})
    with pytest.raises(LookupError):
        edit_ticket(db, tid + 1000, "her", {"bogus": 1})


@pytest.mark.parametrize("data", [{}, {"bogus": 1}, {"title": ""}, None])
def test_value_error_comes_before_permission_error(db, data):
    tid = _ticket(db)
    with pytest.raises(ValueError):
        edit_ticket(db, tid, "him", data)


def test_value_error_comes_before_not_editable(db):
    tid = _ticket(db, "done")
    with pytest.raises(ValueError):
        edit_ticket(db, tid, "her", {"priority": "high"})


def test_permission_error_comes_before_not_editable(db):
    tid = _ticket(db, "closed")
    with pytest.raises(PermissionError):
        edit_ticket(db, tid, "him", {"title": "X"})
