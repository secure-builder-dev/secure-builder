from datetime import date, datetime, timezone
from typing import Any

from app.models import Ticket

USERS = ("her", "him")

ALLOWED_KEYS = {"title", "details", "priority", "due"}
VALID_PRIORITIES = {"low", "normal", "urgent"}


def _parse_date(s: str) -> date:
    """Parse YYYY-MM-DD string into a date object, raising ValueError on invalid input."""
    if not isinstance(s, str):
        raise ValueError("due must be a string in YYYY-MM-DD format")
    parts = s.split("-")
    if len(parts) != 3:
        raise ValueError("due must be in YYYY-MM-DD format")
    try:
        year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
        return date(year, month, day)
    except (ValueError, OverflowError):
        raise ValueError("due must be a valid date in YYYY-MM-DD format") from None


def ticket_to_dict(ticket: Ticket) -> dict[str, Any]:
    """Convert a Ticket model to a plain dict with proper formatting."""
    return {
        "id": ticket.id,
        "title": ticket.title,
        "details": ticket.details,
        "priority": ticket.priority,
        "due": ticket.due.isoformat() if ticket.due is not None else None,
        "status": ticket.status,
        "filed_by": ticket.filed_by,
        "assigned_to": ticket.assigned_to,
        "created_at": ticket.created_at.isoformat(),
        "updated_at": ticket.updated_at.isoformat(),
    }


def create_ticket(session, filed_by: str, data: dict[str, Any]) -> dict[str, Any]:
    """Create a new ticket with validation.
    
    Args:
        session: Database session
        filed_by: User filing the ticket ('her' or 'him')
        data: Dict with title (required), details, priority, due (all optional except title)
    
    Returns:
        ticket_to_dict result for the created ticket
    
    Raises:
        ValueError: If filed_by is not in USERS, data has invalid keys/values, or title is invalid
    """
    # Validate filed_by
    if filed_by not in USERS:
        raise ValueError(f"Unknown user: {filed_by}")
    
    # Validate data keys
    if not isinstance(data, dict):
        raise ValueError("data must be a dict")
    
    extra_keys = set(data.keys()) - ALLOWED_KEYS
    if extra_keys:
        raise ValueError(f"Unknown keys: {extra_keys}")
    
    # Validate and process title (required)
    if "title" not in data:
        raise ValueError("title is required")
    
    raw_title = data["title"]
    if not isinstance(raw_title, str):
        raise ValueError("title must be a string")
    
    title = raw_title.strip()
    if len(title) < 1:
        raise ValueError("title must be at least 1 character after stripping")
    if len(title) > 120:
        raise ValueError("title must be at most 120 characters after stripping")
    
    # Validate details (optional, default "")
    details = data.get("details", "")
    if not isinstance(details, str):
        raise ValueError("details must be a string")
    if len(details) > 1000:
        raise ValueError("details must be at most 1000 characters")
    
    # Validate priority (optional, default "normal")
    priority = data.get("priority", "normal")
    if not isinstance(priority, str):
        raise ValueError("priority must be a string")
    if priority not in VALID_PRIORITIES:
        raise ValueError(f"priority must be one of {VALID_PRIORITIES}")
    
    # Validate due (optional, default None)
    due_raw = data.get("due", None)
    if due_raw is None:
        due: date | None = None
    elif isinstance(due_raw, str):
        due = _parse_date(due_raw)
    else:
        raise ValueError("due must be a string in YYYY-MM-DD format or None")
    
    # Determine assigned_to (the other user)
    assigned_to = "him" if filed_by == "her" else "her"
    
    # Create the ticket
    now = datetime.now(timezone.utc)
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
    
    return ticket_to_dict(ticket)
