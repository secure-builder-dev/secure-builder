"""TO-3c: rules.create_ticket and rules.change_status record their events in the same commit."""
import pytest

from app.models import Ticket, TicketEvent
from app.rules import change_status, create_ticket, ticket_to_dict
from tests.conftest import at, set_times

MOVES = [
    ("open", "acknowledged", "him"),       # assignee
    ("acknowledged", "in_progress", "him"),
    ("in_progress", "done", "him"),
    ("done", "closed", "her"),             # filer
    ("done", "open", "her"),
    ("closed", "open", "her"),
]


def _events(session, tid):
    rows = session.query(TicketEvent).filter(TicketEvent.ticket_id == tid).order_by(TicketEvent.id).all()
    return [(e.kind, e.actor, e.from_status, e.to_status) for e in rows]


def _ticket(db, status="open"):
    t = create_ticket(db, "her", {"title": "Task"})         # filer her, assignee him
    set_times(db, t["id"], updated=at("2026-01-01"), status=status)
    return t["id"]


@pytest.mark.parametrize("filer,other", [("her", "him"), ("him", "her")])
def test_create_ticket_records_one_filed_event(db, filer, other):
    t = create_ticket(db, filer, {"title": "Fix the sink"})
    assert t["filed_by"] == filer and t["assigned_to"] == other
    assert _events(db, t["id"]) == [("filed", filer, None, "open")]


def test_the_filed_event_is_committed_with_the_ticket(db):
    from app.db import SessionLocal
    t = create_ticket(db, "her", {"title": "Stored"})
    other = SessionLocal()
    try:
        assert other.get(Ticket, t["id"]) is not None
        assert _events(other, t["id"]) == [("filed", "her", None, "open")]
        assert other.query(TicketEvent).one().at.tzinfo is not None
    finally:
        other.close()


@pytest.mark.parametrize("data", [{}, {"title": ""}, {"title": "T", "priority": "high"}, {"title": "T", "x": 1}])
def test_a_create_that_raises_records_no_event(db, data):
    with pytest.raises(ValueError):
        create_ticket(db, "her", data)
    db.rollback()
    assert db.query(TicketEvent).count() == 0


def test_a_create_by_an_unknown_filer_records_no_event(db):
    with pytest.raises(ValueError):
        create_ticket(db, "stranger", {"title": "T"})
    db.rollback()
    assert db.query(TicketEvent).count() == 0


@pytest.mark.parametrize("src,dst,who", MOVES)
def test_each_move_records_one_status_event(db, src, dst, who):
    from app.db import SessionLocal
    tid = _ticket(db, src)
    t = change_status(db, tid, who, dst)
    assert t["status"] == dst
    other = SessionLocal()
    try:                                                    # committed together with the move
        assert other.get(Ticket, tid).status == dst
        assert _events(other, tid) == [("filed", "her", None, "open"), ("status", who, src, dst)]
    finally:
        other.close()


def test_a_full_lifecycle_records_every_move_in_order(db):
    tid = create_ticket(db, "her", {"title": "Task"})["id"]
    for dst, who in [("acknowledged", "him"), ("in_progress", "him"), ("done", "him"), ("closed", "her"),
                     ("open", "her")]:
        change_status(db, tid, who, dst)
    assert _events(db, tid) == [
        ("filed", "her", None, "open"),
        ("status", "him", "open", "acknowledged"),
        ("status", "him", "acknowledged", "in_progress"),
        ("status", "him", "in_progress", "done"),
        ("status", "her", "done", "closed"),
        ("status", "her", "closed", "open"),
    ]


def test_events_belong_to_their_own_ticket(db):
    a = create_ticket(db, "her", {"title": "A"})["id"]
    b = create_ticket(db, "him", {"title": "B"})["id"]
    change_status(db, a, "him", "acknowledged")
    assert _events(db, a) == [("filed", "her", None, "open"), ("status", "him", "open", "acknowledged")]
    assert _events(db, b) == [("filed", "him", None, "open")]


@pytest.mark.parametrize("tid_offset,user,dst,exc", [
    (1000, "him", "acknowledged", LookupError),      # missing ticket
    (0, "stranger", "acknowledged", LookupError),    # not a party
    (0, "him", "bogus", ValueError),                 # unknown status
    (0, "him", "done", ValueError),                  # move not in the table
    (0, "him", "open", ValueError),                  # same status
    (0, "her", "acknowledged", PermissionError),     # wrong party
])
def test_a_move_that_raises_records_no_event_and_changes_nothing(db, tid_offset, user, dst, exc):
    tid = _ticket(db, "open")
    before = ticket_to_dict(db.get(Ticket, tid))
    with pytest.raises(exc):
        change_status(db, tid + tid_offset, user, dst)
    db.commit()                                      # whatever the call left pending would be stored now
    db.expire_all()
    assert _events(db, tid) == [("filed", "her", None, "open")]
    assert db.query(TicketEvent).count() == 1
    assert ticket_to_dict(db.get(Ticket, tid)) == before


def test_change_status_still_returns_the_ticket_dict(db):
    tid = _ticket(db, "open")
    t = change_status(db, tid, "him", "acknowledged")
    db.expire_all()
    assert t == ticket_to_dict(db.get(Ticket, tid))
    import datetime as dt
    assert dt.datetime.fromisoformat(t["updated_at"]) > at("2026-01-01")
