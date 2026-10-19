import datetime
from typing import List

from app.models import Ticket, Comment, TicketEvent


def _ensure_ticket_and_user(session, ticket_id: int, user: str) -> Ticket:
    """Fetch ticket and verify *user* is a party (filer or assignee).

    Returns the Ticket object if valid, otherwise raises ``LookupError``.
    """
    ticket = session.get(Ticket, ticket_id)
    if ticket is None:
        raise LookupError("ticket not found")
    # Allow either the filer (the user who created the ticket) or the assignee to view comments or history.
    if user not in (ticket.filed_by, ticket.assigned_to):
        raise LookupError("user not a party to the ticket")
    return ticket


def comment_to_dict(comment: Comment) -> dict:
    """Convert a :class:`Comment` ORM instance to a plain dict.

    All columns are included; ``created_at`` is an ISO‑8601 string.
    """
    created = comment.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=datetime.timezone.utc)
    else:
        created = created.astimezone(datetime.timezone.utc)
    return {
        "id": comment.id,
        "ticket_id": comment.ticket_id,
        "author": comment.author,
        "body": comment.body,
        "created_at": created.isoformat(),
    }


def event_to_dict(event: TicketEvent) -> dict:
    """Convert a :class:`TicketEvent` ORM instance to a plain dict.

    All columns are included; ``at`` is an ISO‑8601 string.
    """
    at = event.at
    if at.tzinfo is None:
        at = at.replace(tzinfo=datetime.timezone.utc)
    else:
        at = at.astimezone(datetime.timezone.utc)
    return {
        "id": event.id,
        "ticket_id": event.ticket_id,
        "actor": event.actor,
        "kind": event.kind,
        "from_status": event.from_status,
        "to_status": event.to_status,
        "at": at.isoformat(),
    }


def record_event(
    session,
    ticket: Ticket,
    actor: str,
    kind: str,
    from_status: str | None = None,
    to_status: str | None = None,
) -> None:
    """Add a :class:`TicketEvent` for *ticket*.

    The event's ``at`` timestamp is the current UTC time (timezone‑aware).
    The function does **not** commit; the caller may commit later.
    """
    now = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
    ev = TicketEvent(
        ticket_id=ticket.id,
        actor=actor,
        kind=kind,
        from_status=from_status,
        to_status=to_status,
        at=now,
    )
    session.add(ev)
    # No commit – caller decides when to persist


def add_comment(session, ticket_id: int, user: str, body) -> dict:
    """Validate and store a comment.

    * Raises ``LookupError`` if the ticket does not exist or *user* is not a party.
    * Raises ``ValueError`` for invalid *body* (type, empty after stripping, >500 chars).
    * Stores the stripped body, commits, and returns ``comment_to_dict`` of the new comment.
    * Does **not** modify the ticket's ``updated_at``.
    """
    # Validate ticket and user
    ticket = _ensure_ticket_and_user(session, ticket_id, user)

    # Validate body
    if not isinstance(body, str):
        raise ValueError("body must be a string")
    stripped = body.strip()
    if not stripped:
        raise ValueError("body cannot be empty after stripping")
    if len(stripped) > 500:
        raise ValueError("body exceeds 500 characters")

    now = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
    comment = Comment(
        ticket_id=ticket.id,
        author=user,
        body=stripped,
        created_at=now,
    )
    session.add(comment)
    session.commit()
    # Refresh to get generated id
    session.refresh(comment)
    return comment_to_dict(comment)


def list_comments(session, ticket_id: int, user: str) -> List[dict]:
    """Return all comments for *ticket_id* as dicts, oldest first.

    Performs the same ticket/user validation as :func:`add_comment`.
    """
    _ensure_ticket_and_user(session, ticket_id, user)
    comments = (
        session.query(Comment)
        .filter(Comment.ticket_id == ticket_id)
        .order_by(Comment.created_at.asc(), Comment.id.asc())
        .all()
    )
    return [comment_to_dict(c) for c in comments]


def ticket_history(session, ticket_id: int, user: str) -> List[dict]:
    """Return all events for *ticket_id* as dicts, ordered by ``at`` then ``id``.

    Performs the same ticket/user validation as :func:`add_comment`.
    """
    _ensure_ticket_and_user(session, ticket_id, user)
    events = (
        session.query(TicketEvent)
        .filter(TicketEvent.ticket_id == ticket_id)
        .order_by(TicketEvent.at.asc(), TicketEvent.id.asc())
        .all()
    )
    return [event_to_dict(e) for e in events]
