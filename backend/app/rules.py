import datetime
from typing import Any, Dict

from app.models import Ticket

# Fixed users for the system
USERS = ("her", "him")


def ticket_to_dict(ticket: Ticket) -> Dict[str, Any]:
    """Convert a :class:`Ticket` ORM object to a plain dictionary.

    The dictionary contains all columns defined on the model. ``due`` is
    represented as a ``YYYY-MM-DD`` string when present, otherwise ``None``.
    ``created_at`` and ``updated_at`` are ISO‑8601 strings.
    """
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


def _validate_title(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("title must be a string")
    stripped = value.strip()
    if not (1 <= len(stripped) <= 120):
        raise ValueError("title length must be 1‑120 after stripping")
    return stripped


def _validate_details(value: Any) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError("details must be a string")
    if len(value) > 1000:
        raise ValueError("details too long")
    return value


def _validate_priority(value: Any) -> str:
    if value is None:
        return "normal"
    if not isinstance(value, str):
        raise ValueError("priority must be a string")
    if value not in {"low", "normal", "urgent"}:
        raise ValueError("invalid priority")
    return value


def _validate_due(value: Any) -> datetime.date | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("due must be a string or None")
    try:
        # fromisoformat validates the format and the actual calendar date
        return datetime.date.fromisoformat(value)
    except Exception as exc:
        raise ValueError("invalid due date") from exc


def create_ticket(session, filed_by: str, data: dict) -> dict:
    """Create a new ticket.

    ``session`` – a SQLAlchemy session.
    ``filed_by`` – must be one of :data:`USERS`.
    ``data`` – may contain only ``title``, ``details``, ``priority`` and ``due``.
    Returns the newly created ticket as a plain dict via :func:`ticket_to_dict`.
    """
    # Validate filed_by
    if filed_by not in USERS:
        raise ValueError("filed_by must be one of USERS")

    # Ensure data is a dict
    if not isinstance(data, dict):
        raise ValueError("data must be a dict")

    allowed_keys = {"title", "details", "priority", "due"}
    extra_keys = set(data.keys()) - allowed_keys
    if extra_keys:
        raise ValueError(f"unexpected keys: {extra_keys}")

    # Title is required
    if "title" not in data:
        raise ValueError("title is required")

    title = _validate_title(data["title"])
    details = _validate_details(data.get("details", ""))
    priority = _validate_priority(data.get("priority", None))
    due = _validate_due(data.get("due", None))

    # Determine the assignee – the other user
    assigned_to = USERS[1] if filed_by == USERS[0] else USERS[0]

    now = datetime.datetime.now(datetime.timezone.utc)

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
    session.refresh(ticket)
    return ticket_to_dict(ticket)
