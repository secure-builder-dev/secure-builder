"""TO-3b: activity.py -- comment_to_dict, event_to_dict, record_event, add_comment, list_comments, ticket_history."""
import datetime as dt

import pytest

from app import activity
from app.models import Comment, Ticket, TicketEvent

OLD = dt.datetime(2026, 1, 1, 12, tzinfo=dt.timezone.utc)
UTC = dt.timezone.utc


def _ticket(db, filer="her"):
    """A stored ticket built directly (so no 'filed' event of a later bead is involved); filer -> other user."""
    t = Ticket(title="Task", details="d", priority="normal", due=None, status="open", filed_by=filer,
               assigned_to="him" if filer == "her" else "her", created_at=OLD, updated_at=OLD)
    db.add(t)
    db.commit()
    return t


def _near_now(value):
    return abs(dt.datetime.now(UTC) - value) < dt.timedelta(minutes=1)


def test_comment_to_dict_has_every_column(db):
    t = _ticket(db)
    c = Comment(ticket_id=t.id, author="him", body="hi", created_at=OLD)
    db.add(c)
    db.commit()
    d = activity.comment_to_dict(c)
    assert set(d) == {"id", "ticket_id", "author", "body", "created_at"}
    assert (d["id"], d["ticket_id"], d["author"], d["body"]) == (c.id, t.id, "him", "hi")
    assert isinstance(d["created_at"], str)
    assert dt.datetime.fromisoformat(d["created_at"]) == OLD


def test_event_to_dict_has_every_column(db):
    t = _ticket(db)
    e = TicketEvent(ticket_id=t.id, actor="him", kind="status", from_status="open", to_status="acknowledged", at=OLD)
    db.add(e)
    db.commit()
    d = activity.event_to_dict(e)
    assert set(d) == {"id", "ticket_id", "actor", "kind", "from_status", "to_status", "at"}
    assert (d["id"], d["ticket_id"], d["actor"], d["kind"]) == (e.id, t.id, "him", "status")
    assert (d["from_status"], d["to_status"]) == ("open", "acknowledged")
    assert isinstance(d["at"], str)
    assert dt.datetime.fromisoformat(d["at"]) == OLD


def test_record_event_adds_an_event_stored_by_the_next_commit(db):
    from app.db import SessionLocal
    t = _ticket(db)
    activity.record_event(db, t, "him", "status", from_status="open", to_status="acknowledged")
    other = SessionLocal()
    try:
        assert other.query(TicketEvent).count() == 0          # not committed by record_event
        db.commit()
        [e] = other.query(TicketEvent).all()
    finally:
        other.close()
    assert (e.ticket_id, e.actor, e.kind, e.from_status, e.to_status) == (t.id, "him", "status", "open", "acknowledged")
    assert e.at.tzinfo is not None and e.at.utcoffset() is not None
    assert _near_now(e.at)


def test_record_event_defaults_to_no_statuses_and_is_lost_on_rollback(db):
    t = _ticket(db)
    tid = t.id
    activity.record_event(db, t, "her", "edited")
    db.commit()
    [e] = db.query(TicketEvent).all()
    assert (e.ticket_id, e.actor, e.kind, e.from_status, e.to_status) == (tid, "her", "edited", None, None)
    activity.record_event(db, db.get(Ticket, tid), "her", "edited")
    db.rollback()
    assert db.query(TicketEvent).count() == 1


@pytest.mark.parametrize("user", ["her", "him"])
def test_add_comment_by_either_party(db, user):
    from app.db import SessionLocal
    t = _ticket(db)
    d = activity.add_comment(db, t.id, user, "  Done soon  ")
    assert set(d) == {"id", "ticket_id", "author", "body", "created_at"}
    assert (d["ticket_id"], d["author"], d["body"]) == (t.id, user, "Done soon")
    assert _near_now(dt.datetime.fromisoformat(d["created_at"]))
    other = SessionLocal()
    try:
        stored = other.get(Comment, d["id"])
        assert stored.body == "Done soon"
        assert activity.comment_to_dict(stored) == d
    finally:
        other.close()


def test_add_comment_leaves_the_ticket_unchanged(db):
    from app.rules import ticket_to_dict
    t = _ticket(db)
    before = ticket_to_dict(t)
    activity.add_comment(db, t.id, "him", "note")
    db.expire_all()
    assert ticket_to_dict(db.get(Ticket, t.id)) == before
    assert db.get(Ticket, t.id).updated_at == OLD


@pytest.mark.parametrize("tid_offset,user", [(1000, "her"), (0, "stranger"), (0, ""), (0, None)])
def test_add_comment_missing_ticket_or_non_party_raises_lookup_error(db, tid_offset, user):
    t = _ticket(db)
    with pytest.raises(LookupError):
        activity.add_comment(db, t.id + tid_offset, user, "hello")
    assert db.query(Comment).count() == 0


@pytest.mark.parametrize("body", [None, 5, ["x"], "", "   ", "x" * 501, " " + "y" * 501 + " "])
def test_add_comment_invalid_body_raises_value_error(db, body):
    t = _ticket(db)
    with pytest.raises(ValueError):
        activity.add_comment(db, t.id, "her", body)
    db.rollback()
    assert db.query(Comment).count() == 0


def test_add_comment_allows_500_characters_after_stripping(db):
    t = _ticket(db)
    assert activity.add_comment(db, t.id, "her", "  " + "z" * 500 + "\n")["body"] == "z" * 500


def test_list_comments_only_this_ticket_oldest_first_then_id(db):
    t, other_t = _ticket(db), _ticket(db, filer="him")
    late = Comment(ticket_id=t.id, author="her", body="late", created_at=OLD + dt.timedelta(days=2))
    tie1 = Comment(ticket_id=t.id, author="him", body="tie1", created_at=OLD)
    tie2 = Comment(ticket_id=t.id, author="her", body="tie2", created_at=OLD)
    early = Comment(ticket_id=t.id, author="him", body="early", created_at=OLD - dt.timedelta(days=1))
    elsewhere = Comment(ticket_id=other_t.id, author="her", body="elsewhere", created_at=OLD)
    for c in (late, tie1, tie2, early, elsewhere):
        db.add(c)
        db.commit()                                        # ids rise in this order
    got = activity.list_comments(db, t.id, "him")
    assert [c["body"] for c in got] == ["early", "tie1", "tie2", "late"]
    assert got[0] == activity.comment_to_dict(early)
    assert activity.list_comments(db, other_t.id, "her") == [activity.comment_to_dict(elsewhere)]


def test_ticket_history_only_this_ticket_oldest_first_then_id(db):
    t, other_t = _ticket(db), _ticket(db, filer="him")
    rows = [
        TicketEvent(ticket_id=t.id, actor="him", kind="status", from_status="open", to_status="acknowledged",
                    at=OLD + dt.timedelta(hours=5)),
        TicketEvent(ticket_id=t.id, actor="her", kind="edited", at=OLD + dt.timedelta(hours=1)),
        TicketEvent(ticket_id=t.id, actor="her", kind="edited", at=OLD + dt.timedelta(hours=1)),
        TicketEvent(ticket_id=t.id, actor="her", kind="filed", to_status="open", at=OLD),
        TicketEvent(ticket_id=other_t.id, actor="him", kind="filed", to_status="open", at=OLD),
    ]
    for r in rows:
        db.add(r)
        db.commit()
    got = activity.ticket_history(db, t.id, "her")
    assert [e["id"] for e in got] == [rows[3].id, rows[1].id, rows[2].id, rows[0].id]
    assert got[-1] == activity.event_to_dict(rows[0])
    assert [e["id"] for e in activity.ticket_history(db, other_t.id, "her")] == [rows[4].id]


def test_lists_are_empty_without_rows(db):
    t = _ticket(db)
    assert activity.list_comments(db, t.id, "her") == []
    assert activity.ticket_history(db, t.id, "him") == []


@pytest.mark.parametrize("fn", [activity.list_comments, activity.ticket_history])
def test_lists_raise_lookup_error_for_missing_ticket_or_non_party(db, fn):
    t = _ticket(db)
    with pytest.raises(LookupError):
        fn(db, t.id + 1000, "her")
    with pytest.raises(LookupError):
        fn(db, t.id, "stranger")
