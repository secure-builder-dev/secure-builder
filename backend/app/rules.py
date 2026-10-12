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