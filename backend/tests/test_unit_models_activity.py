"""TO-3a: the Comment and TicketEvent models, and init_db creating their tables."""
import datetime as dt

import pytest
from sqlalchemy import DateTime, Integer, String, inspect
from sqlalchemy.exc import IntegrityError

WHEN = dt.datetime(2026, 10, 1, 9, 0, tzinfo=dt.timezone.utc)


def _fk_targets(column):
    return {fk.target_fullname for fk in column.foreign_keys}


def _ticket(db):
    from app.models import Ticket
    t = Ticket(title="T", details="", priority="normal", due=None, status="open", filed_by="her",
               assigned_to="him", created_at=WHEN, updated_at=WHEN)
    db.add(t)
    db.commit()
    return t.id


def test_comment_table_and_columns():
    from app.models import Comment
    assert Comment.__tablename__ == "comments"
    cols = Comment.__table__.columns
    assert set(cols.keys()) == {"id", "ticket_id", "author", "body", "created_at"}
    assert cols["id"].primary_key
    assert isinstance(cols["id"].type, Integer)
    assert isinstance(cols["ticket_id"].type, Integer)
    assert _fk_targets(cols["ticket_id"]) == {"tickets.id"}
    assert isinstance(cols["author"].type, String)
    assert isinstance(cols["body"].type, String)
    assert cols["body"].type.length == 500
    assert isinstance(cols["created_at"].type, DateTime)
    assert cols["created_at"].type.timezone is True


def test_ticket_event_table_and_columns():
    from app.models import TicketEvent
    assert TicketEvent.__tablename__ == "ticket_events"
    cols = TicketEvent.__table__.columns
    assert set(cols.keys()) == {"id", "ticket_id", "actor", "kind", "from_status", "to_status", "at"}
    assert cols["id"].primary_key
    assert isinstance(cols["id"].type, Integer)
    assert isinstance(cols["ticket_id"].type, Integer)
    assert _fk_targets(cols["ticket_id"]) == {"tickets.id"}
    for name in ("actor", "kind", "from_status", "to_status"):
        assert isinstance(cols[name].type, String)
    assert cols["from_status"].nullable
    assert cols["to_status"].nullable
    assert isinstance(cols["at"].type, DateTime)
    assert cols["at"].type.timezone is True


def test_ticket_model_is_unchanged():
    from app.models import Ticket
    assert Ticket.__tablename__ == "tickets"
    assert set(Ticket.__table__.columns.keys()) == {"id", "title", "details", "priority", "due", "status",
                                                     "filed_by", "assigned_to", "created_at", "updated_at"}
    assert not Ticket.__table__.foreign_keys


def test_init_db_creates_all_three_tables():
    from app.db import Base, engine, init_db
    import app.models  # noqa: F401
    Base.metadata.drop_all(engine)
    init_db()
    try:
        names = set(inspect(engine).get_table_names())
        assert {"tickets", "comments", "ticket_events"} <= names
    finally:
        engine.dispose()
        Base.metadata.drop_all(engine)


def test_comment_round_trips(db):
    from app.models import Comment
    tid = _ticket(db)
    c = Comment(ticket_id=tid, author="her", body="x" * 500, created_at=WHEN)
    db.add(c)
    db.commit()
    db.expire_all()
    got = db.get(Comment, c.id)
    assert isinstance(got.id, int)
    assert got.ticket_id == tid
    assert got.author == "her"
    assert got.body == "x" * 500
    assert got.created_at == WHEN


def test_ticket_event_round_trips_with_and_without_statuses(db):
    from app.models import TicketEvent
    tid = _ticket(db)
    moved = TicketEvent(ticket_id=tid, actor="him", kind="status", from_status="open", to_status="acknowledged",
                        at=WHEN)
    edited = TicketEvent(ticket_id=tid, actor="her", kind="edited", from_status=None, to_status=None, at=WHEN)
    db.add_all([moved, edited])
    db.commit()
    db.expire_all()
    a = db.get(TicketEvent, moved.id)
    b = db.get(TicketEvent, edited.id)
    assert (a.ticket_id, a.actor, a.kind, a.from_status, a.to_status) == (tid, "him", "status", "open", "acknowledged")
    assert a.at == WHEN
    assert (b.kind, b.from_status, b.to_status) == ("edited", None, None)


@pytest.mark.parametrize("which", ["comment", "event"])
def test_ticket_id_must_name_an_existing_ticket(db, which):
    from app.models import Comment, TicketEvent
    if which == "comment":
        row = Comment(ticket_id=999999, author="her", body="b", created_at=WHEN)
    else:
        row = TicketEvent(ticket_id=999999, actor="her", kind="filed", from_status=None, to_status="open", at=WHEN)
    db.add(row)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
