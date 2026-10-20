import datetime as dt

from app.models import Comment, Ticket, TicketEvent


def _iso(value):
    return value.astimezone(dt.timezone.utc).isoformat()


def comment_to_dict(comment):
    return {
        "id": comment.id,
        "ticket_id": comment.ticket_id,
        "author": comment.author,
        "body": comment.body,
        "created_at": _iso(comment.created_at),
    }


def event_to_dict(event):
    return {
        "id": event.id,
        "ticket_id": event.ticket_id,
        "actor": event.actor,
        "kind": event.kind,
        "from_status": event.from_status,
        "to_status": event.to_status,
        "at": _iso(event.at),
    }


def record_event(session, ticket, actor, kind, from_status=None, to_status=None):
    session.add(TicketEvent(
        ticket_id=ticket.id,
        actor=actor,
        kind=kind,
        from_status=from_status,
        to_status=to_status,
        at=dt.datetime.now(dt.timezone.utc),
    ))


def _get_ticket(session, ticket_id, user):
    ticket = session.get(Ticket, ticket_id)
    if ticket is None or user not in (ticket.filed_by, ticket.assigned_to):
        raise LookupError("ticket not found")
    return ticket


def add_comment(session, ticket_id, user, body):
    ticket = _get_ticket(session, ticket_id, user)
    if not isinstance(body, str):
        raise ValueError("body must be a string")
    stripped = body.strip()
    if not (1 <= len(stripped) <= 500):
        raise ValueError("body must be 1 to 500 characters after stripping")
    comment = Comment(
        ticket_id=ticket.id,
        author=user,
        body=stripped,
        created_at=dt.datetime.now(dt.timezone.utc),
    )
    session.add(comment)
    session.commit()
    return comment_to_dict(comment)


def list_comments(session, ticket_id, user):
    _get_ticket(session, ticket_id, user)
    rows = (
        session.query(Comment)
        .filter(Comment.ticket_id == ticket_id)
        .order_by(Comment.created_at, Comment.id)
        .all()
    )
    return [comment_to_dict(c) for c in rows]


def ticket_history(session, ticket_id, user):
    _get_ticket(session, ticket_id, user)
    rows = (
        session.query(TicketEvent)
        .filter(TicketEvent.ticket_id == ticket_id)
        .order_by(TicketEvent.at, TicketEvent.id)
        .all()
    )
    return [event_to_dict(e) for e in rows]
