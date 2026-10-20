import datetime as dt
from typing import Any, Dict, Mapping

from app.models import Ticket

# Fixed users for the system.
USERS = ("her", "him")


def _validate_filed_by(filed_by: Any) -> None:
    """Validate that the filer is one of the known users.

    Raises:
        ValueError: If ``filed_by`` is not a member of :data:`USERS`.
    """
    if filed_by not in USERS:
        raise ValueError("filed_by must be one of the known users")


def _validate_data(data: Mapping[str, Any]) -> Dict[str, Any]:
    """Validate the incoming ``data`` dict for ticket creation.

    Returns a dict with only the allowed keys and default values applied.
    Raises ``ValueError`` on any validation problem.
    """
    if not isinstance(data, Mapping):
        raise ValueError("data must be a mapping")

    allowed_keys = {"title", "details", "priority", "due"}
    extra = set(data) - allowed_keys
    if extra:
        raise ValueError(f"unexpected keys: {extra}")

    # Title – required
    if "title" not in data:
        raise ValueError("title is required")
    title = data["title"]
    if not isinstance(title, str):
        raise ValueError("title must be a string")
    title = title.strip()
    if not (1 <= len(title) <= 120):
        raise ValueError("title length must be 1..120 after stripping")

    # Details – optional
    details = data.get("details", "")
    if not isinstance(details, str):
        raise ValueError("details must be a string")
    if len(details) > 1000:
        raise ValueError("details length must be <= 1000")

    # Priority – optional
    priority = data.get("priority", "normal")
    if not isinstance(priority, str):
        raise ValueError("priority must be a string")
    if priority not in {"low", "normal", "urgent"}:
        raise ValueError("priority must be one of 'low', 'normal', 'urgent'")

    # Due – optional
    due_raw = data.get("due", None)
    if due_raw is None:
        due = None
    else:
        if not isinstance(due_raw, str):
            raise ValueError("due must be a string in YYYY-MM-DD format or None")
        try:
            due = dt.date.fromisoformat(due_raw)
        except Exception as exc:
            raise ValueError("due must be a valid date in YYYY-MM-DD format") from exc

    return {
        "title": title,
        "details": details,
        "priority": priority,
        "due": due,
    }


def ticket_to_dict(ticket: Ticket) -> Dict[str, Any]:
    """Convert a :class:`Ticket` ORM instance to a plain ``dict``.

    The dict contains all columns required by the tests. ``due`` is formatted as
    ``YYYY-MM-DD`` or ``None``. ``created_at`` and ``updated_at`` are ISO‑8601
    strings.
    """
    result: Dict[str, Any] = {
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
    return result


def create_ticket(session, filed_by: Any, data: Mapping[str, Any]):
    """Create a new ticket record.

    Parameters
    ----------
    session: SQLAlchemy session (already bound to the test DB).
    filed_by: The user filing the ticket – must be one of :data:`USERS`.
    data: Mapping containing ticket fields. Only ``title`` is required; optional
    keys are ``details``, ``priority`` and ``due``.

    Returns
    -------
    dict
        The newly created ticket represented as a plain dictionary.

    Raises
    ------
    ValueError
        If any validation fails.
    """
    # Validate the filer first.
    _validate_filed_by(filed_by)

    # Validate and normalise the payload.
    clean = _validate_data(data)

    # Determine the assignee – the other user.
    assigned_to = USERS[1] if filed_by == USERS[0] else USERS[0]

    now = dt.datetime.now(dt.timezone.utc)
    ticket = Ticket(
        title=clean["title"],
        details=clean["details"],
        priority=clean["priority"],
        due=clean["due"],
        status="open",
        filed_by=filed_by,
        assigned_to=assigned_to,
        created_at=now,
        updated_at=now,
    )
    session.add(ticket)
    session.commit()
    # Refresh to get the generated primary key.
    session.refresh(ticket)
    return ticket_to_dict(ticket)


def change_status(session, ticket_id, user, new_status):
    """Change the status of a ticket according to the design table.

    Raises:
        LookupError: if the ticket does not exist or user is not a party.
        ValueError: if new_status is unknown or the transition is not allowed.
        PermissionError: if the user is not the party allowed to make the transition.
    """
    # Lookup ticket
    ticket = session.get(Ticket, ticket_id)
    if ticket is None:
        raise LookupError("ticket not found")
    # Verify user is a party
    if user not in (ticket.filed_by, ticket.assigned_to):
        raise LookupError("user not a party")
    # Validate new_status
    allowed_statuses = {"open", "acknowledged", "in_progress", "done", "closed"}
    if new_status not in allowed_statuses:
        raise ValueError("unknown status")
    # Define allowed moves
    moves = {
        ("open", "acknowledged"): "assignee",
        ("acknowledged", "in_progress"): "assignee",
        ("in_progress", "done"): "assignee",
        ("done", "closed"): "filer",
        ("done", "open"): "filer",
        ("closed", "open"): "filer",
    }
    cur = ticket.status
    key = (cur, new_status)
    if key not in moves:
        raise ValueError("invalid transition")
    required_party = moves[key]
    # Determine which party the user is
    if required_party == "assignee":
        if user != ticket.assigned_to:
            raise PermissionError("only assignee may perform this move")
    else:  # filer
        if user != ticket.filed_by:
            raise PermissionError("only filer may perform this move")
    # Perform move
    ticket.status = new_status
    ticket.updated_at = dt.datetime.now(dt.timezone.utc)
    session.commit()
    return ticket_to_dict(ticket)
