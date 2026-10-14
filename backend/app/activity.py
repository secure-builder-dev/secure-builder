from datetime import datetime, timezone

from app.models import Comment, TicketEvent, Ticket
from sqlalchemy import select, and_


def comment_to_dict(comment: Comment) -> dict:
    """Convert a Comment model instance to a plain dict.
    
    - created_at: ISO-8601 string (datetime.isoformat())
    """
    return {
        'id': comment.id,
        'ticket_id': comment.ticket_id,
        'author': comment.author,
        'body': comment.body,
        'created_at': comment.created_at.astimezone(timezone.utc).isoformat()
    }


def event_to_dict(event: TicketEvent) -> dict:
    """Convert a TicketEvent model instance to a plain dict.
    
    - at: ISO-8601 string (datetime.isoformat())
    """
    return {
        'id': event.id,
        'ticket_id': event.ticket_id,
        'actor': event.actor,
        'kind': event.kind,
        'from_status': event.from_status,
        'to_status': event.to_status,
        'at': event.at.astimezone(timezone.utc).isoformat()
    }


def record_event(session, ticket: Ticket, actor: str, kind: str, from_status: str | None = None, to_status: str | None = None) -> TicketEvent:
    """Record a ticket event.
    
    Args:
        session: Database session
        ticket: The ticket this event is for
        actor: User who performed the action
        kind: Type of event ('filed', 'status', 'edited')
        from_status: Previous status (for status changes)
        to_status: New status (for status changes)
    
    Returns:
        The created TicketEvent instance (not committed)
    """
    event = TicketEvent(
        ticket_id=ticket.id,
        actor=actor,
        kind=kind,
        from_status=from_status,
        to_status=to_status,
        at=datetime.now(timezone.utc)
    )
    session.add(event)
    session.flush()
    # Do not commit - caller commits
    return event


def _validate_comment_body(body: str) -> str:
    """Validate and process comment body.
    
    Returns stripped body if valid, raises ValueError otherwise.
    """
    if not isinstance(body, str):
        raise ValueError("body must be a string")
    
    stripped = body.strip()
    
    if len(stripped) < 1:
        raise ValueError("body must be at least 1 character after stripping")
    
    if len(stripped) > 500:
        raise ValueError("body must be at most 500 characters after stripping")
    
    return stripped


def _check_ticket_access(session, ticket_id: int, user: str) -> Ticket:
    """Check if a ticket exists and user is a party.
    
    Args:
        session: Database session
        ticket_id: ID of the ticket
        user: User to check access for
    
    Returns:
        The Ticket instance if accessible
    
    Raises:
        LookupError: If ticket does not exist or user is not a party
    """
    stmt = select(Ticket).where(Ticket.id == ticket_id)
    ticket = session.execute(stmt).scalars().first()
    
    if ticket is None:
        raise LookupError(f"Ticket {ticket_id} not found")
    
    if user != ticket.filed_by and user != ticket.assigned_to:
        raise LookupError(f"User '{user}' is not a party to ticket {ticket_id}")
    
    return ticket


def add_comment(session, ticket_id: int, user: str, body: str) -> dict:
    """Add a comment to a ticket.
    
    Args:
        session: Database session
        ticket_id: ID of the ticket
        user: User adding the comment (must be filer or assignee)
        body: Comment text
    
    Returns:
        comment_to_dict of the created comment
    
    Raises:
        LookupError: If ticket does not exist or user is not a party
        ValueError: If body is invalid
    """
    # Check ticket access first
    _check_ticket_access(session, ticket_id, user)
    
    # Validate body
    stripped_body = _validate_comment_body(body)
    
    # Create comment
    comment = Comment(
        ticket_id=ticket_id,
        author=user,
        body=stripped_body,
        created_at=datetime.now(timezone.utc)
    )
    
    session.add(comment)
    session.commit()
    
    return comment_to_dict(comment)


def list_comments(session, ticket_id: int, user: str) -> list:
    """List all comments for a ticket.
    
    Args:
        session: Database session
        ticket_id: ID of the ticket
        user: User requesting comments (must be filer or assignee)
    
    Returns:
        List of comment_to_dict dicts, ordered by created_at then id (oldest first)
    
    Raises:
        LookupError: If ticket does not exist or user is not a party
    """
    # Check ticket access first
    _check_ticket_access(session, ticket_id, user)
    
    # Query comments for this ticket, ordered by created_at then id
    stmt = select(Comment).where(
        Comment.ticket_id == ticket_id
    ).order_by(Comment.created_at.asc(), Comment.id.asc())
    
    comments = session.execute(stmt).scalars().all()
    
    # Sort in Python to ensure correct ordering when created_at values are equal
    sorted_comments = sorted(comments, key=lambda c: (c.created_at, c.id))
    
    return [comment_to_dict(c) for c in sorted_comments]


def ticket_history(session, ticket_id: int, user: str) -> list:
    """List all events for a ticket.
    
    Args:
        session: Database session
        ticket_id: ID of the ticket
        user: User requesting history (must be filer or assignee)
    
    Returns:
        List of event_to_dict dicts, ordered by at then id (oldest first)
    
    Raises:
        LookupError: If ticket does not exist or user is not a party
    """
    # Check ticket access first
    _check_ticket_access(session, ticket_id, user)
    
    # Query events for this ticket, ordered by at then id
    stmt = select(TicketEvent).where(
        TicketEvent.ticket_id == ticket_id
    ).order_by(TicketEvent.at.asc(), TicketEvent.id.asc())
    
    events = session.execute(stmt).scalars().all()
    
    return [event_to_dict(e) for e in events]
