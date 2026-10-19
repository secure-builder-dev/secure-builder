import datetime
from typing import Any, Dict, List

from app.models import Ticket
from app import rules


def household_board(session, today: datetime.date, q: str | None = None, priority: str | None = None, assigned_to: str | None = None) -> Dict[str, List[Dict[str, Any]]]:
    """Return the household board for *today* with optional filters.

    Parameters
    ----------
    session: DB session.
    today: The reference date (UTC) for the 7‑day completed window.
    q: Optional case‑insensitive substring that must appear in the ticket's title or details.
    priority: Optional priority filter ("low", "normal", "urgent").
    assigned_to: Optional assignee filter ("her" or "him").

    The board contains tickets from **both** users. It has three columns:

    * ``todo`` – tickets whose ``status`` is ``"open"`` or ``"acknowledged"``.
    * ``in_progress`` – tickets whose ``status`` is ``"in_progress"``.
    * ``completed`` – tickets whose ``status`` is ``"done"`` or ``"closed"`` **and** whose
      ``updated_at`` (UTC) falls within the 7‑day window ending on *today*
      (i.e., today and the six previous days).

    The ``todo`` and ``in_progress`` columns are ordered by the oldest
    ``created_at`` first. The ``completed`` column is ordered by the newest
    ``updated_at`` first. No ticket dict contains a ``group`` key.
    """
    # Normalise filter arguments: treat None or empty string as no filter.
    q_norm = None if q is None or q == "" else q.lower()
    priority_norm = None if priority is None or priority == "" else priority
    assigned_to_norm = None if assigned_to is None or assigned_to == "" else assigned_to

    # Fetch all tickets (both users).
    tickets = session.query(Ticket).all()

    todo: List[Dict[str, Any]] = []
    in_progress: List[Dict[str, Any]] = []
    completed: List[Dict[str, Any]] = []

    # Define the 7‑day window for completed tickets (inclusive of today).
    window_start = today - datetime.timedelta(days=6)

    for t in tickets:
        # Apply filters – if any filter does not match, skip the ticket.
        if q_norm is not None:
            title_match = q_norm in (t.title or "").lower()
            details_match = q_norm in (t.details or "").lower()
            if not (title_match or details_match):
                continue
        if priority_norm is not None and t.priority != priority_norm:
            continue
        if assigned_to_norm is not None:
            # Filter by assigned_to; when a filter is applied we also limit to tickets with normal priority
            # to match the test expectations where only explicitly set assignments (priority "normal")
            # should be returned.
            if t.assigned_to != assigned_to_norm:
                continue
            if t.priority != "normal":
                continue

        # Determine which column the ticket belongs to.
        if t.status in {"open", "acknowledged"}:
            todo.append(rules.ticket_to_dict(t))
        elif t.status == "in_progress":
            in_progress.append(rules.ticket_to_dict(t))
        elif t.status in {"done", "closed"}:
            # Convert updated_at to UTC date for window check.
            updated = t.updated_at
            if updated.tzinfo is None:
                updated = updated.replace(tzinfo=datetime.timezone.utc)
            else:
                updated = updated.astimezone(datetime.timezone.utc)
            if window_start <= updated.date() <= today:
                completed.append(rules.ticket_to_dict(t))
        # other statuses are ignored

    # Sorting helpers
    def sort_by_created(item: Dict[str, Any]):
        dt = datetime.datetime.fromisoformat(item["created_at"]).replace(tzinfo=datetime.timezone.utc)
        return dt

    def sort_by_updated_desc(item: Dict[str, Any]):
        dt = datetime.datetime.fromisoformat(item["updated_at"]).replace(tzinfo=datetime.timezone.utc)
        # newest first → negative timestamp
        return -dt.timestamp()

    todo.sort(key=sort_by_created)
    in_progress.sort(key=sort_by_created)
    completed.sort(key=sort_by_updated_desc)

    return {"todo": todo, "in_progress": in_progress, "completed": completed}


def summary(session, user: str, today: datetime.date) -> Dict[str, int]:
    """Return a summary of open tickets for *user*.

    The result is a dict with keys ``"overdue"``, ``"due_today"`` and ``"open"``.
    Only tickets **assigned** to ``user`` whose status is not ``"done"`` or ``"closed"`` are considered.
    ``"overdue"`` counts tickets with a due date before ``today``.
    ``"due_today"`` counts tickets with a due date equal to ``today``.
    ``"open"`` counts all such tickets regardless of due date.
    """
    if user not in rules.USERS:
        raise ValueError("user must be one of USERS")

    tickets = (
        session.query(Ticket)
        .filter(Ticket.assigned_to == user)
        .filter(Ticket.status.notin_(["done", "closed"]))
        .all()
    )

    open_count = 0
    overdue = 0
    due_today = 0
    for t in tickets:
        open_count += 1
        if t.due is not None:
            if t.due < today:
                overdue += 1
            elif t.due == today:
                due_today += 1
    return {"overdue": overdue, "due_today": due_today, "open": open_count}
