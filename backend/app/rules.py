from datetime import date, datetime, timezone, timedelta
from typing import Any

from app.db import SessionLocal
from app.models import Ticket

USERS = ("her", "him")

VALID_PRIORITIES = {"low", "normal", "urgent"}
VALID_STATUSES = {"open", "acknowledged", "in_progress", "done", "closed"}

STATUS_MOVES = {
    ("open", "acknowledged"): "assignee",
    ("acknowledged", "in_progress"): "assignee",
    ("in_progress", "done"): "assignee",
    ("done", "closed"): "filer",
    ("done", "open"): "filer",
    ("closed", "open"): "filer",
}


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _ticket_to_dict(t: Ticket) -> dict[str, Any]:
    due_val = None
    if t.due is not None:
        due_val = t.due.isoformat()
    return {
        "id": t.id,
        "title": t.title,
        "details": t.details,
        "priority": t.priority,
        "due": due_val,
        "status": t.status,
        "filed_by": t.filed_by,
        "assigned_to": t.assigned_to,
        "created_at": t.created_at.isoformat(),
        "updated_at": t.updated_at.isoformat(),
    }


def create_ticket(session: SessionLocal, filed_by: str, data: dict[str, Any]) -> dict[str, Any]:
    if filed_by not in USERS:
        raise ValueError("filed_by is not a valid user")

    allowed_keys = {"title", "details", "priority", "due"}
    if not set(data.keys()).issubset(allowed_keys):
        extra = set(data.keys()) - allowed_keys
        raise ValueError(f"unknown key in data: {extra.pop()}")

    title_raw = data.get("title")
    if title_raw is None:
        raise ValueError("title is missing")
    title = title_raw.strip()
    if not (1 <= len(title) <= 120):
        raise ValueError("title must be 1-120 characters after stripping")

    details_raw = data.get("details", "")
    if not isinstance(details_raw, str):
        raise ValueError("details must be a string")
    if len(details_raw) > 1000:
        raise ValueError("details exceeds 1000 characters")
    details = details_raw

    priority = data.get("priority", "normal")
    if priority not in VALID_PRIORITIES:
        raise ValueError(f"invalid priority: {priority}")

    due_str = data.get("due")
    due = None
    if due_str is not None:
        if not isinstance(due_str, str):
            raise ValueError("due must be a string or null")
        try:
            due = date.fromisoformat(due_str)
        except ValueError:
            raise ValueError(f"invalid date format: {due_str}")

    assigned_to = "him" if filed_by == "her" else "her"
    now = _now_utc()

    ticket = Ticket(
        title=title,
        details=details,
        priority=priority,
        due=due,
        status="open",
        filed_by=filed_by,
        assigned_to=assigned_to,
        created_at=now,
        updated_at=now,
    )
    session.add(ticket)
    session.commit()
    return _ticket_to_dict(ticket)


def change_status(session: SessionLocal, ticket_id: int, user: str, new_status: str) -> dict[str, Any]:
    ticket = session.get(Ticket, ticket_id)
    if ticket is None:
        raise LookupError("ticket not found")

    if user not in (ticket.filed_by, ticket.assigned_to):
        raise LookupError("user is not a party to this ticket")

    if new_status not in VALID_STATUSES:
        raise ValueError(f"unknown status: {new_status}")

    current_status = ticket.status
    move_key = (current_status, new_status)
    if move_key not in STATUS_MOVES:
        raise ValueError(f"status move from {current_status} to {new_status} is not allowed")

    required_party = STATUS_MOVES[move_key]
    if required_party == "assignee" and user != ticket.assigned_to:
        raise PermissionError("only the assignee can make this move")
    if required_party == "filer" and user != ticket.filed_by:
        raise PermissionError("only the filer can make this move")

    ticket.status = new_status
    ticket.updated_at = _now_utc()
    session.commit()
    return _ticket_to_dict(ticket)


def _compute_group(priority: str, due: date | None, today: date) -> int:
    if priority == "urgent":
        return 0
    if due is not None and due < today:
        return 0
    if due is not None and due >= today and due <= today + timedelta(days=3):
        return 1
    return 2


def dashboard(session: SessionLocal, user: str, today: date) -> dict[str, list[dict[str, Any]]]:
    from sqlalchemy import select
    todo_query = (
        session.execute(
            select(Ticket)
            .filter(Ticket.assigned_to == user)
            .filter(Ticket.status.in_("open", "acknowledged"))
        ).scalars().all()
    )
    in_progress_query = (
        session.execute(
            select(Ticket)
            .filter(Ticket.assigned_to == user)
            .filter(Ticket.status == "in_progress")
        ).scalars().all()
    )

    def _sort_key(t: Ticket):
        group = _compute_group(t.priority, t.due, today)
        due_sort = t.due if t.due is not None else date.max
        return (group, due_sort, t.created_at)

    todo_tickets = sorted(todo_query.all(), key=_sort_key)
    in_progress_tickets = sorted(in_progress_query.all(), key=_sort_key)

    def _add_group(t: Ticket) -> dict[str, Any]:
        d = _ticket_to_dict(t)
        d["group"] = _compute_group(t.priority, t.due, today)
        return d

    todo_list = [_add_group(t) for t in todo_tickets]
    in_progress_list = [_add_group(t) for t in in_progress_tickets]

    from sqlalchemy import select
    seven_days_ago = today - timedelta(days=7)
    completed_query = (
        session.execute(
            select(Ticket)
            .filter(Ticket.assigned_to == user)
            .filter(Ticket.status.in_("done", "closed"))
            .filter(
                Ticket.updated_at >= datetime.combine(seven_days_ago, datetime.min.time(), tzinfo=timezone.utc),
                Ticket.updated_at < datetime.combine(today + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
            )
        ).scalars().all()
    )
    completed_tickets = sorted(
        completed_query,
        key=lambda t: t.updated_at,
        reverse=True
    )
    completed_list = [_ticket_to_dict(t) for t in completed_tickets]

    return {
        "todo": todo_list,
        "in_progress": in_progress_list,
        "completed": completed_list,
    }


def filed(session: SessionLocal, user: str) -> list[dict[str, Any]]:
    from sqlalchemy import select
    tickets = (
        session.execute(
            select(Ticket)
            .filter(Ticket.filed_by == user)
            .order_by(Ticket.created_at.desc())
        ).scalars().all()
    )
    return [_ticket_to_dict(t) for t in tickets]