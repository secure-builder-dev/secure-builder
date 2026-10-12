"""GD-1b: USERS, create_ticket and ticket_to_dict."""
import datetime as dt
from typing import Any

from sqlalchemy import select

from app.db import Base
from app.models import Ticket

USERS = ("her", "him")


def ticket_to_dict(ticket: Ticket) -> dict[str, Any]:
    return {
        "id": ticket.id,
        "title": ticket.title,
        "details": ticket.details,
        "priority": ticket.priority,
        "due": ticket.due.isoformat() if ticket.due else None,
        "status": ticket.status,
        "filed_by": ticket.filed_by,
        "assigned_to": ticket.assigned_to,
        "created_at": ticket.created_at.isoformat(),
        "updated_at": ticket.updated_at.isoformat(),
    }


def create_ticket(session, filed_by: str, data: dict[str, Any]) -> dict[str, Any]:
    if filed_by not in USERS:
        raise ValueError("filed_by must be one of USERS")

    if not isinstance(data, dict):
        raise ValueError("data must be a dict")

    allowed_keys = {"title", "details", "priority", "due"}
    if not allowed_keys.issuperset(data.keys()):
        raise ValueError("data contains unknown keys")

    title = data.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("title must be a non-empty string")
    if len(title.strip()) > 120:
        raise ValueError("title must be at most 120 characters")

    details = data.get("details", "")
    if not isinstance(details, str):
        raise ValueError("details must be a string")
    if len(details) > 1000:
        raise ValueError("details must be at most 1000 characters")

    priority = data.get("priority", "normal")
    if priority not in {"low", "normal", "urgent"}:
        raise ValueError("priority must be one of 'low', 'normal', 'urgent'")

    due = data.get("due")
    if due is not None:
        if not isinstance(due, str):
            raise ValueError("due must be a string or None")
        try:
            due_date = dt.datetime.strptime(due, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError("due must be in YYYY-MM-DD format")
    else:
        due_date = None

    now = dt.datetime.now(dt.timezone.utc)
    assigned_to = "him" if filed_by == "her" else "her"

    ticket = Ticket(
        title=title.strip(),
        details=details,
        priority=priority,
        due=due_date,
        status="open",
        filed_by=filed_by,
        assigned_to=assigned_to,
        created_at=now,
        updated_at=now,
    )

    session.add(ticket)
    session.commit()

    return ticket_to_dict(ticket)


def change_status(session, ticket_id: int, user: str, new_status: str) -> dict[str, Any]:
    # Validate user
    if user not in USERS:
        raise LookupError("user is neither filer nor assignee")

    # Fetch ticket
    ticket = session.get(Ticket, ticket_id)
    if ticket is None:
        raise LookupError("ticket not found")

    # Check if user is a party
    if user not in (ticket.filed_by, ticket.assigned_to):
        raise LookupError("user is neither filer nor assignee")

    # Validate new_status
    valid_statuses = ["open", "acknowledged", "in_progress", "done", "closed"]
    if new_status not in valid_statuses:
        raise ValueError("new_status must be one of open, acknowledged, in_progress, done, closed")

    # Check if move is in the table
    allowed_moves = {
        ("open", "acknowledged"): "assignee",
        ("acknowledged", "in_progress"): "assignee",
        ("in_progress", "done"): "assignee",
        ("done", "closed"): "filer",
        ("done", "open"): "filer",
        ("closed", "open"): "filer",
    }
    move = (ticket.status, new_status)
    if move not in allowed_moves:
        raise ValueError("move not in the table")

    # Check if user has permission
    required_party = allowed_moves[move]
    if (required_party == "assignee" and user != ticket.assigned_to) or \
       (required_party == "filer" and user != ticket.filed_by):
        raise PermissionError("user does not have permission for this move")

    # Update ticket
    ticket.status = new_status
    ticket.updated_at = dt.datetime.now(dt.timezone.utc)
    session.commit()

    return ticket_to_dict(ticket)


def dashboard(session, user: str, today: dt.date) -> dict[str, list[dict[str, Any]]]:
    """Return the personal board for the given user."""
    if user not in USERS:
        raise LookupError("user is neither filer nor assignee")

    # Get all tickets assigned to the user
    tickets = session.query(Ticket).filter(Ticket.assigned_to == user).all()

    todo = []
    in_progress = []
    completed = []

    for ticket in tickets:
        t_dict = ticket_to_dict(ticket)
        
        # Determine group for todo and in_progress
        group = None
        if ticket.status in ("open", "acknowledged"):
            if ticket.priority == "urgent" or (ticket.due and ticket.due < today):
                group = 0
            elif ticket.due and (ticket.due <= today + dt.timedelta(days=3)):
                group = 1
            else:
                group = 2
            t_dict["group"] = group
            todo.append(t_dict)
        elif ticket.status == "in_progress":
            if ticket.priority == "urgent" or (ticket.due and ticket.due < today):
                group = 0
            elif ticket.due and (ticket.due <= today + dt.timedelta(days=3)):
                group = 1
            else:
                group = 2
            t_dict["group"] = group
            in_progress.append(t_dict)
        elif ticket.status in ("done", "closed"):
            # Check if updated_at is within the 7 days ending today
            updated_date = ticket.updated_at.date()
            if updated_date >= today - dt.timedelta(days=6) and updated_date <= today:
                completed.append(t_dict)

    # Sort todo and in_progress by group, then due, then created_at
    def sort_key(t):
        due = t.get("due")
        if due is None:
            due = dt.date.max
        else:
            due = dt.datetime.strptime(due, "%Y-%m-%d").date()
        created = dt.datetime.fromisoformat(t["created_at"]).date()
        return (t.get("group", 2), due, created)

    todo.sort(key=sort_key)
    in_progress.sort(key=sort_key)

    # Sort completed by updated_at newest first
    completed.sort(key=lambda t: dt.datetime.fromisoformat(t["updated_at"]), reverse=True)

    return {
        "todo": todo,
        "in_progress": in_progress,
        "completed": completed,
    }


def filed(session, user: str) -> list[dict[str, Any]]:
    """Return all tickets filed by the given user."""
    if user not in USERS:
        raise LookupError("user is neither filer nor assignee")

    # Get all tickets filed by the user
    tickets = session.query(Ticket).filter(Ticket.filed_by == user).all()

    # Convert to dict and sort by created_at newest first
    result = [ticket_to_dict(ticket) for ticket in tickets]
    result.sort(key=lambda t: dt.datetime.fromisoformat(t["created_at"]), reverse=True)

    return result