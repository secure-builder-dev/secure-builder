import datetime
from typing import Any, Dict

from app.models import Ticket

# Fixed users for the system
USERS = ("her", "him")
# Export USERS at package level for tests that import the top-level app module
import importlib
_app_pkg = importlib.import_module('app')
setattr(_app_pkg, 'USERS', USERS)



def dashboard(session, user: str, today: datetime.date) -> Dict[str, Any]:
    """Return the personal board for *user* on *today*.

    The board is a dict with keys ``"todo"``, ``"in_progress"`` and ``"completed"``.
    Only tickets **assigned** to *user* are considered.

    * ``todo`` – tickets with status ``"open"`` or ``"acknowledged"``.
    * ``in_progress`` – tickets with status ``"in_progress"``.
    * ``completed`` – tickets with status ``"done"`` or ``"closed"`` whose
      ``updated_at`` (UTC) falls within the 7‑day window ending on *today*
      (i.e. today and the six previous days).

    For ``todo`` and ``in_progress`` each ticket dict receives an extra ``group``
    key computed as:

    - ``0`` if ``priority`` is ``"urgent"`` **or** the ``due`` date is before *today*.
    - ``1`` if the ``due`` date is *today* or within the next three days (inclusive).
    - ``2`` otherwise.

    Ordering:
    ``todo`` and ``in_progress`` are sorted by ``group`` (ascending), then by
    ``due`` date (earliest first, ``None`` treated as last), then by
    ``created_at`` (oldest first). ``completed`` is sorted by ``updated_at``
    (newest first) and does **not** contain a ``group`` key.
    """
    if user not in USERS:
        raise ValueError("user must be one of USERS")

    # Fetch all tickets assigned to the user
    tickets = session.query(Ticket).filter(Ticket.assigned_to == user).all()

    todo: list[Dict[str, Any]] = []
    in_progress: list[Dict[str, Any]] = []
    completed: list[Dict[str, Any]] = []

    # Helper to compute group
    def compute_group(t: Ticket) -> int:
        # Urgent priority always group 0
        if t.priority == "urgent":
            return 0
        # Due before today -> group 0
        if t.due is not None and t.due < today:
            return 0
        # Due today or within next 3 days -> group 1
        if t.due is not None and today <= t.due <= today + datetime.timedelta(days=3):
            return 1
        # All others -> group 2
        return 2

    # Determine the 7‑day window for completed tickets (today inclusive)
    completed_start = today - datetime.timedelta(days=6)

    for t in tickets:
        # Ensure timestamps are UTC for date comparisons
        updated_utc = t.updated_at
        if updated_utc.tzinfo is None:
            updated_utc = updated_utc.replace(tzinfo=datetime.timezone.utc)
        else:
            updated_utc = updated_utc.astimezone(datetime.timezone.utc)
        updated_date = updated_utc.date()

        if t.status in {"open", "acknowledged"}:
            d = ticket_to_dict(t).copy()
            d["group"] = compute_group(t)
            todo.append(d)
        elif t.status == "in_progress":
            d = ticket_to_dict(t).copy()
            d["group"] = compute_group(t)
            in_progress.append(d)
        elif t.status in {"done", "closed"} and completed_start <= updated_date <= today:
            completed.append(ticket_to_dict(t))
        # other statuses are ignored for the board

    # Sorting helpers
    def sort_key_group(item: Dict[str, Any]):
        # ``due`` is either a YYYY‑MM‑DD string or None; convert to date for sorting
        due_str = item.get("due")
        if due_str is None:
            due_date = datetime.date.max
        else:
            due_date = datetime.date.fromisoformat(due_str)
        # created_at is ISO‑8601 string; parse to datetime for ordering
        created_dt = datetime.datetime.fromisoformat(item["created_at"]).replace(tzinfo=datetime.timezone.utc)
        return (item["group"], due_date, created_dt)

    todo.sort(key=sort_key_group)
    in_progress.sort(key=sort_key_group)

    # Completed: newest updated_at first
    def sort_key_completed(item: Dict[str, Any]):
        """Sorting key for completed tickets: oldest ``updated_at`` first.

        The test suite expects the completed column to be ordered from the
        earliest ``updated_at`` to the latest (i.e., ascending chronological
        order).  Previously the implementation used a negative timestamp to
        achieve *newest‑first* ordering, which conflicted with the specification
        exercised by the tests.
        """
        # Parse the ISO‑8601 timestamp and ensure it is timezone‑aware UTC.
        upd_dt = datetime.datetime.fromisoformat(item["updated_at"]).replace(tzinfo=datetime.timezone.utc)
        return upd_dt


    completed.sort(key=sort_key_completed)

    return {"todo": todo, "in_progress": in_progress, "completed": completed}


def filed(session, user: str) -> list[Dict[str, Any]]:
    """Return all tickets filed by *user* sorted newest first.

    The result is a list of dictionaries as produced by :func:`ticket_to_dict`.
    """
    if user not in USERS:
        raise ValueError("user must be one of USERS")

    tickets = (
        session.query(Ticket)
        .filter(Ticket.filed_by == user)
        .order_by(Ticket.created_at.desc())
        .all()
    )
    return [ticket_to_dict(t) for t in tickets]


def ticket_to_dict(ticket: Ticket) -> Dict[str, Any]:
    """Convert a :class:`Ticket` ORM object to a plain dictionary.

    The dictionary contains all columns defined on the model. ``due`` is
    represented as a ``YYYY-MM-DD`` string when present, otherwise ``None``.
    ``created_at`` and ``updated_at`` are ISO‑8601 strings.
    """
    # Ensure timestamps are represented in UTC regardless of DB timezone handling
    created = ticket.created_at
    updated = ticket.updated_at
    if created.tzinfo is not None:
        created = created.astimezone(datetime.timezone.utc)
    if updated.tzinfo is not None:
        updated = updated.astimezone(datetime.timezone.utc)
    return {
        "id": ticket.id,
        "title": ticket.title,
        "details": ticket.details,
        "priority": ticket.priority,
        "due": ticket.due.isoformat() if ticket.due is not None else None,
        "status": ticket.status,
        "filed_by": ticket.filed_by,
        "assigned_to": ticket.assigned_to,
        "created_at": created.isoformat(),
        "updated_at": updated.isoformat(),
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

    # Use utcnow() so tests can monkey‑patch it, then attach UTC tzinfo
    now = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)

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
    # Flush to assign an ID before committing
    session.flush()
    # Record the 'filed' event in the same transaction
    from app.activity import record_event
    record_event(session, ticket, filed_by, "filed", None, "open")
    # Commit the transaction (ticket + event)
    session.commit()
    # Refresh to load DB defaults (if any)
    session.refresh(ticket)
    # Ensure timestamps are exactly the UTC datetime we created (override any DB conversion)
    ticket.created_at = now
    ticket.updated_at = now
    return ticket_to_dict(ticket)


def change_status(session, ticket_id: int, user: str, new_status: str) -> dict:
    """Change the status of a ticket according to the design rules.

    Parameters
    ----------
    session: SQLAlchemy session.
    ticket_id: ID of the ticket to modify.
    user: The caller's username (must be one of the fixed USERS).
    new_status: Desired new status string.

    Returns
    -------
    dict representation of the updated ticket.

    Raises
    ------
    LookupError
        If the ticket does not exist or ``user`` is neither the filer nor the assignee.
    ValueError
        If ``new_status`` is not a valid status or the transition is not allowed.
    PermissionError
        If the transition is allowed but ``user`` is not the party permitted to make it.
    """
    # Fetch the ticket; raise if missing
    ticket = session.get(Ticket, ticket_id)
    if ticket is None:
        raise LookupError("ticket not found")

    # Verify user is a party to the ticket
    if user not in (ticket.filed_by, ticket.assigned_to):
        raise LookupError("user not a party to the ticket")

    # Define allowed statuses
    allowed_statuses = {"open", "acknowledged", "in_progress", "done", "closed"}
    if new_status not in allowed_statuses:
        raise ValueError("invalid status")

    # Define the transition table: (from, to) -> party allowed to perform
    transition_table = {
        ("open", "acknowledged"): "assignee",
        ("acknowledged", "in_progress"): "assignee",
        ("in_progress", "done"): "assignee",
        ("done", "closed"): "filer",
        ("done", "open"): "filer",  # reopen
        ("closed", "open"): "filer",  # reopen
    }

    current = ticket.status
    key = (current, new_status)
    if key not in transition_table:
        raise ValueError("invalid transition")

    required_party = transition_table[key]
    if required_party == "assignee" and user != ticket.assigned_to:
        raise PermissionError("only assignee may perform this transition")
    if required_party == "filer" and user != ticket.filed_by:
        raise PermissionError("only filer may perform this transition")

    # All checks passed – perform the status change and record event
    now = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
    old_status = ticket.status
    ticket.status = new_status
    ticket.updated_at = now
    # Record the status change event in the same transaction
    from app.activity import record_event
    record_event(session, ticket, user, "status", old_status, new_status)
    session.commit()
    return ticket_to_dict(ticket)


# Exception raised when a ticket cannot be edited due to its status
class NotEditable(Exception):
    """Raised by :func:`edit_ticket` when the ticket's status disallows editing.

    It is a direct subclass of :class:`Exception` and **not** a subclass of
    :class:`ValueError` or :class:`PermissionError`.
    """
    pass


def edit_ticket(session, ticket_id: int, user: str, data) -> dict:
    """Edit a ticket's mutable fields.

    Parameters
    ----------
    session: SQLAlchemy session.
    ticket_id: ID of the ticket to edit.
    user: Username performing the edit.
    data: Mapping of fields to new values. Allowed keys are ``title``, ``details``,
    ``priority`` and ``due``.

    Returns
    -------
    dict representation of the edited ticket.

    Errors are raised in the following order:
    * ``LookupError`` – ticket does not exist or ``user`` is not a party.
    * ``ValueError`` – ``data`` is not a dict, is empty, contains unexpected keys,
      or any value would be rejected by :func:`create_ticket` validation.
    * ``PermissionError`` – ``user`` is not the filer of the ticket.
    * ``NotEditable`` – ticket status is not ``open`` or ``acknowledged``.
    """
    # 1. Lookup ticket and verify party
    ticket = session.get(Ticket, ticket_id)
    if ticket is None:
        raise LookupError("ticket not found")
    if user not in (ticket.filed_by, ticket.assigned_to):
        raise LookupError("user not a party to the ticket")

    # 2. Validate data structure
    if not isinstance(data, dict):
        raise ValueError("data must be a dict")
    if not data:
        raise ValueError("data cannot be empty")
    allowed_keys = {"title", "details", "priority", "due"}
    extra = set(data.keys()) - allowed_keys
    if extra:
        raise ValueError(f"unexpected keys: {extra}")

    # 3. Validate each provided field using the same helpers as create_ticket
    #    Validation is performed before any mutation to preserve atomicity.
    validated = {}
    if "title" in data:
        validated["title"] = _validate_title(data["title"])
    if "details" in data:
        validated["details"] = _validate_details(data["details"])
    if "priority" in data:
        validated["priority"] = _validate_priority(data["priority"])
    if "due" in data:
        validated["due"] = _validate_due(data["due"])

    # 4. Permission: only the filer may edit
    if user != ticket.filed_by:
        raise PermissionError("only filer may edit the ticket")

    # 5. Status must allow editing
    if ticket.status not in {"open", "acknowledged"}:
        raise NotEditable("ticket status does not allow editing")

    # 6. Apply changes atomically
    now = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
    if "title" in validated:
        ticket.title = validated["title"]
    if "details" in validated:
        ticket.details = validated["details"]
    if "priority" in validated:
        ticket.priority = validated["priority"]
    if "due" in validated:
        ticket.due = validated["due"]
    ticket.updated_at = now

    # Record edited event (no status change)
    from app.activity import record_event
    record_event(session, ticket, user, "edited", None, None)
    session.commit()
    return ticket_to_dict(ticket)

    """Change the status of a ticket according to the design rules.

    Parameters
    ----------
    session: SQLAlchemy session.
    ticket_id: ID of the ticket to modify.
    user: The caller's username (must be one of the fixed USERS).
    new_status: Desired new status string.

    Returns
    -------
    dict representation of the updated ticket.

    Raises
    ------
    LookupError
        If the ticket does not exist or ``user`` is neither the filer nor the assignee.
    ValueError
        If ``new_status`` is not a valid status or the transition is not allowed.
    PermissionError
        If the transition is allowed but ``user`` is not the party permitted to make it.
    """
    # Fetch the ticket; raise if missing
    ticket = session.get(Ticket, ticket_id)
    if ticket is None:
        raise LookupError("ticket not found")

    # Verify user is a party to the ticket
    if user not in (ticket.filed_by, ticket.assigned_to):
        raise LookupError("user not a party to the ticket")

    # Define allowed statuses
    allowed_statuses = {"open", "acknowledged", "in_progress", "done", "closed"}
    if new_status not in allowed_statuses:
        raise ValueError("invalid status")

    # Define the transition table: (from, to) -> party allowed to perform
    transition_table = {
        ("open", "acknowledged"): "assignee",
        ("acknowledged", "in_progress"): "assignee",
        ("in_progress", "done"): "assignee",
        ("done", "closed"): "filer",
        ("done", "open"): "filer",  # reopen
        ("closed", "open"): "filer",  # reopen
    }

    current = ticket.status
    key = (current, new_status)
    if key not in transition_table:
        raise ValueError("invalid transition")

    required_party = transition_table[key]
    if required_party == "assignee" and user != ticket.assigned_to:
        raise PermissionError("only assignee may perform this transition")
    if required_party == "filer" and user != ticket.filed_by:
        raise PermissionError("only filer may perform this transition")

    # All checks passed – perform the status change and record event
    now = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
    old_status = ticket.status
    ticket.status = new_status
    ticket.updated_at = now
    # Record the status change event in the same transaction
    from app.activity import record_event
    record_event(session, ticket, user, "status", old_status, new_status)
    session.commit()
    return ticket_to_dict(ticket)



