import datetime
import pytest
from sqlalchemy import inspect

from app.activity import (
    comment_to_dict,
    event_to_dict,
    record_event,
    add_comment,
    list_comments,
    ticket_history,
)
from app.models import Ticket, Comment, TicketEvent
from app.rules import create_ticket, USERS

# Helper to create a ticket for a given filer
def _make_ticket(db, filer="her", title="Test Ticket"):
    ticket_dict = create_ticket(db, filed_by=filer, data={"title": title})
    ticket = db.get(Ticket, ticket_dict["id"])
    return ticket

def test_comment_and_event_to_dict_returns_all_fields_with_iso_strings(db):
    # Create a ticket and a comment/event manually
    ticket = _make_ticket(db)
    now = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
    comment = Comment(ticket_id=ticket.id, author="her", body="hello", created_at=now)
    event = TicketEvent(ticket_id=ticket.id, actor="him", kind="status", from_status="open", to_status="acknowledged", at=now)
    db.add_all([comment, event])
    db.flush()

    c_dict = comment_to_dict(comment)
    e_dict = event_to_dict(event)

    # All columns should be present
    assert set(c_dict.keys()) == {"id", "ticket_id", "author", "body", "created_at"}
    assert set(e_dict.keys()) == {"id", "ticket_id", "actor", "kind", "from_status", "to_status", "at"}

    # ISO‑8601 strings for timestamps
    for key in ["created_at"]:
        assert isinstance(c_dict[key], str)
        # parsing should succeed
        datetime.datetime.fromisoformat(c_dict[key])
    for key in ["at"]:
        assert isinstance(e_dict[key], str)
        datetime.datetime.fromisoformat(e_dict[key])

def test_record_event_adds_event_without_commit_and_uses_utc_now(db):
    ticket = _make_ticket(db)
    before = datetime.datetime.now(datetime.timezone.utc)
    # Record event – should not commit automatically
    record_event(db, ticket, actor="her", kind="status", from_status="open", to_status="acknowledged")
    after = datetime.datetime.now(datetime.timezone.utc)

    # Event should be pending in the session (new or dirty)
    pending = [obj for obj in db.new if isinstance(obj, TicketEvent)]
    assert len(pending) == 1
    ev = pending[0]
    # 'at' should be between before and after
    assert before <= ev.at <= after
    assert ev.at.tzinfo is not None
    # Not yet persisted – rollback should remove it
    db.rollback()
    assert db.query(TicketEvent).filter(TicketEvent.id == ev.id).first() is None

def test_add_comment_validates_and_creates_comment(db):
    ticket = _make_ticket(db)
    # Invalid ticket id
    with pytest.raises(LookupError):
        add_comment(db, ticket_id=9999, user="her", body="test")
    # User not party
    with pytest.raises(LookupError):
        add_comment(db, ticket_id=ticket.id, user="him", body="test")
    # Invalid body types
    for bad_body in [123, None, [], {}]:
        with pytest.raises(ValueError):
            add_comment(db, ticket_id=ticket.id, user="her", body=bad_body)
    # Empty after stripping
    with pytest.raises(ValueError):
        add_comment(db, ticket_id=ticket.id, user="her", body="   ")
    # Over 500 chars after stripping
    long_body = "a" * 501
    with pytest.raises(ValueError):
        add_comment(db, ticket_id=ticket.id, user="her", body=long_body)
    # Valid comment
    comment_dict = add_comment(db, ticket_id=ticket.id, user="her", body="  hello world  ")
    # Should be committed – can query
    stored = db.query(Comment).filter(Comment.id == comment_dict["id"]).one()
    assert stored.body == "hello world"
    assert stored.author == "her"
    # returned dict matches comment_to_dict
    assert comment_dict == comment_to_dict(stored)

def test_add_comment_does_not_modify_ticket_updated_at(db):
    ticket = _make_ticket(db)
    original_updated = ticket.updated_at
    # Add comment as filer (her)
    add_comment(db, ticket_id=ticket.id, user="her", body="note")
    db.refresh(ticket)
    assert ticket.updated_at == original_updated

def test_list_comments_and_ticket_history_sort_and_errors(db):
    ticket = _make_ticket(db)
    # Create two comments with different timestamps
    now = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
    c1 = Comment(ticket_id=ticket.id, author="her", body="first", created_at=now - datetime.timedelta(seconds=10))
    c2 = Comment(ticket_id=ticket.id, author="her", body="second", created_at=now)
    db.add_all([c1, c2])
    db.flush()
    # List comments – should be ordered oldest first then id
    comments = list_comments(db, ticket_id=ticket.id, user="her")
    assert [c["id"] for c in comments] == [c1.id, c2.id]

    # Create events with same timestamps but different ids
    ev1 = TicketEvent(ticket_id=ticket.id, actor="her", kind="status", from_status=None, to_status="open", at=now - datetime.timedelta(seconds=5))
    ev2 = TicketEvent(ticket_id=ticket.id, actor="her", kind="status", from_status="open", to_status="acknowledged", at=now - datetime.timedelta(seconds=5))
    db.add_all([ev1, ev2])
    db.flush()
    events = ticket_history(db, ticket_id=ticket.id, user="her")
    # Should be ordered by at then id (ids increasing)
    assert [e["id"] for e in events] == sorted([ev1.id, ev2.id])

    # Errors for missing ticket or unauthorized user
    with pytest.raises(LookupError):
        list_comments(db, ticket_id=9999, user="her")
    with pytest.raises(LookupError):
        ticket_history(db, ticket_id=9999, user="her")
    # Unauthorized user
    with pytest.raises(LookupError):
        list_comments(db, ticket_id=ticket.id, user="him")
    with pytest.raises(LookupError):
        ticket_history(db, ticket_id=ticket.id, user="him")
