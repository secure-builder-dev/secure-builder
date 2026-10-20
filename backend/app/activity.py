import datetime as dt
from typing import List, Dict, Any

from app.models import Comment, TicketEvent, Ticket


def comment_to_dict(comment: Comment) -> Dict[str, Any]:
    """Convert a :class:`Comment` ORM instance to a plain ``dict``.

    The dict contains all columns, with ``created_at`` as an ISO‑8601 string.
    """
    return {
        "id": comment.id,
        "ticket_id": comment.ticket_id,
        "author": comment.author,
        "body": comment.body,
        "created_at": comment.created_at.isoformat(),
    }


def event_to_dict(event: TicketEvent) -> Dict[str, Any]:
    """Convert a :class:`TicketEvent` ORM instance to a plain ``dict``.

    The dict contains all columns, with ``at`` as an ISO‑8601 string.
    """
    return {
        "id": event.id,
        "ticket_id": event.ticket_id,
        "actor": event.actor,
        "kind": event.kind,
        "from_status": event.from_status,
        "to_status": event.to_status,
        "at": event.at.isoformat(),
    }


def record_event(session, ticket: Ticket, actor: str, kind: str, *, from_status: Any = None, to_status: Any = None) -> None:
    """Add a :class:`TicketEvent` for *ticket*.

    The event is added to *session* but **not** committed; the caller's next
    commit will persist it. ``at`` is set to the current UTC time.
    """
    ev = TicketEvent(
        ticket_id=ticket.id,
        actor=actor,
        kind=kind,
        from_status=from_status,
        to_status=to_status,
        at=dt.datetime.now(dt.timezone.utc),
    )
    session.add(ev)
    # No commit here – caller decides when to persist.


def _validate_ticket_and_user(session, ticket_id: int, user: str) -> Ticket:
    """Helper to fetch a ticket and verify *user* is a party.

    Raises ``LookupError`` if the ticket does not exist or the user is not the
    filer nor the assignee.
    """
    ticket = session.get(Ticket, ticket_id)
    if ticket is None:
        raise LookupError("ticket not found")
    if user not in (ticket.filed_by, ticket.assigned_to):
        raise LookupError("user not a party of the ticket")
    return ticket


def add_comment(session, ticket_id: int, user: str, body: Any) -> Dict[str, Any]:
    """Add a comment to a ticket.

    Validation steps (in order):
    1. Ticket must exist and *user* must be the filer or assignee – otherwise
       ``LookupError``.
    2. ``body`` must be a ``str``; after ``strip()`` it must be non‑empty and
       at most 500 characters – otherwise ``ValueError``.
    The comment is stored with ``created_at`` set to the current UTC time, the
    session is committed, and the comment dict is returned.
    The ticket's ``updated_at`` is **not** modified.
    """
    # Step 1 – ticket existence and party check.
    ticket = _validate_ticket_and_user(session, ticket_id, user)

    # Step 2 – body validation.
    if not isinstance(body, str):
        raise ValueError("body must be a string")
    stripped = body.strip()
    if not stripped:
        raise ValueError("body cannot be empty after stripping")
    if len(stripped) > 500:
        raise ValueError("body exceeds 500 characters after stripping")

    comment = Comment(
        ticket_id=ticket.id,
        author=user,
        body=stripped,
        created_at=dt.datetime.now(dt.timezone.utc),
    )
    session.add(comment)
    session.commit()
    # Refresh to obtain generated primary key.
    session.refresh(comment)
    return comment_to_dict(comment)


def list_comments(session, ticket_id: int, user: str) -> List[Dict[str, Any]]:
    """Return all comments for *ticket_id* visible to *user*.

    Raises ``LookupError`` if the ticket does not exist or *user* is not a party.
    The comments are ordered by ``created_at`` (oldest first) then ``id``.
    """
    _validate_ticket_and_user(session, ticket_id, user)
    comments = (
        session.query(Comment)
        .filter(Comment.ticket_id == ticket_id)
        .order_by(Comment.created_at.asc(), Comment.id.asc())
        .all()
    )
    return [comment_to_dict(c) for c in comments]


def ticket_history(session, ticket_id: int, user: str) -> List[Dict[str, Any]]:
    """Return the event history for *ticket_id* visible to *user*.

    Raises ``LookupError`` if the ticket does not exist or *user* is not a party.
    Events are ordered by ``at`` (oldest first) then ``id``.
    """
    _validate_ticket_and_user(session, ticket_id, user)
    events = (
        session.query(TicketEvent)
        .filter(TicketEvent.ticket_id == ticket_id)
        .order_by(TicketEvent.at.asc(), TicketEvent.id.asc())
        .all()
    )
    return [event_to_dict(e) for e in events]
