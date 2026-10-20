import datetime as dt

from app.activity import record_event
from app.models import Ticket

USERS = ("her", "him")

_PRIORITIES = ("low", "normal", "urgent")
_ALLOWED_KEYS = {"title", "details", "priority", "due"}


def ticket_to_dict(ticket):
    return {
        "id": ticket.id,
        "title": ticket.title,
        "details": ticket.details,
        "priority": ticket.priority,
        "due": ticket.due.isoformat() if ticket.due is not None else None,
        "status": ticket.status,
        "filed_by": ticket.filed_by,
        "assigned_to": ticket.assigned_to,
        "created_at": ticket.created_at.astimezone(dt.timezone.utc).isoformat(),
        "updated_at": ticket.updated_at.astimezone(dt.timezone.utc).isoformat(),
    }


def _parse_due(value):
    if value is None:
        return None
    if not isinstance(value, str) or len(value) != 10:
        raise ValueError("due must be a YYYY-MM-DD string")
    year, month, day = value.split("-")
    if not (year.isdigit() and month.isdigit() and day.isdigit()):
        raise ValueError("due must be a YYYY-MM-DD string")
    try:
        return dt.date(int(year), int(month), int(day))
    except ValueError:
        raise ValueError("due must name a real date in YYYY-MM-DD form")


_STATUSES = ("open", "acknowledged", "in_progress", "done", "closed")
_MOVES = {
    ("open", "acknowledged"): "assignee",
    ("acknowledged", "in_progress"): "assignee",
    ("in_progress", "done"): "assignee",
    ("done", "closed"): "filer",
    ("done", "open"): "filer",
    ("closed", "open"): "filer",
}


def change_status(session, ticket_id, user, new_status):
    ticket = session.get(Ticket, ticket_id)
    if ticket is None or user not in (ticket.filed_by, ticket.assigned_to):
        raise LookupError("ticket not found")
    if new_status not in _STATUSES:
        raise ValueError("unknown status")
    party = _MOVES.get((ticket.status, new_status))
    if party is None:
        raise ValueError("invalid transition")
    expected = ticket.assigned_to if party == "assignee" else ticket.filed_by
    if user != expected:
        raise PermissionError("not allowed to make this move")
    old_status = ticket.status
    ticket.status = new_status
    ticket.updated_at = dt.datetime.now(dt.timezone.utc)
    record_event(session, ticket, user, "status", old_status, new_status)
    session.commit()
    return ticket_to_dict(ticket)


def _group(ticket, today):
    if ticket.priority == "urgent" or (ticket.due is not None and ticket.due < today):
        return 0
    if ticket.due is not None and today <= ticket.due <= today + dt.timedelta(days=3):
        return 1
    return 2


def _ordered_column(tickets, today):
    def key(t):
        return (_group(t, today), t.due is None, t.due or dt.date.max, t.created_at)
    out = []
    for t in sorted(tickets, key=key):
        d = ticket_to_dict(t)
        d["group"] = _group(t, today)
        out.append(d)
    return out


def dashboard(session, user, today):
    tickets = session.query(Ticket).filter(Ticket.assigned_to == user).all()
    todo = [t for t in tickets if t.status in ("open", "acknowledged")]
    in_progress = [t for t in tickets if t.status == "in_progress"]
    window_start = today - dt.timedelta(days=6)
    completed = [
        t for t in tickets
        if t.status in ("done", "closed") and window_start <= t.updated_at.date() <= today
    ]
    completed.sort(key=lambda t: t.updated_at, reverse=True)
    return {
        "todo": _ordered_column(todo, today),
        "in_progress": _ordered_column(in_progress, today),
        "completed": [ticket_to_dict(t) for t in completed],
    }


def filed(session, user):
    tickets = session.query(Ticket).filter(Ticket.filed_by == user).all()
    tickets.sort(key=lambda t: t.created_at, reverse=True)
    return [ticket_to_dict(t) for t in tickets]


def create_ticket(session, filed_by, data):
    if filed_by not in USERS:
        raise ValueError("filed_by must be one of USERS")
    if not isinstance(data, dict) or any(key not in _ALLOWED_KEYS for key in data):
        raise ValueError("data may hold only title, details, priority and due")

    if "title" not in data:
        raise ValueError("title is required")
    title = data["title"]
    if not isinstance(title, str):
        raise ValueError("title must be a string")
    title = title.strip()
    if not (1 <= len(title) <= 120):
        raise ValueError("title must be 1 to 120 characters after stripping")

    details = data.get("details", "")
    if not isinstance(details, str) or len(details) > 1000:
        raise ValueError("details must be a string of at most 1000 characters")

    priority = data.get("priority", "normal")
    if priority not in _PRIORITIES:
        raise ValueError("priority must be one of low, normal or urgent")

    due = _parse_due(data.get("due"))

    now = dt.datetime.now(dt.timezone.utc)
    ticket = Ticket(
        title=title,
        details=details,
        priority=priority,
        due=due,
        status="open",
        filed_by=filed_by,
        assigned_to=("him" if filed_by == "her" else "her"),
        created_at=now,
        updated_at=now,
    )
    session.add(ticket)
    session.flush()
    record_event(session, ticket, filed_by, "filed", None, "open")
    session.commit()
    return ticket_to_dict(ticket)
