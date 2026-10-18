import datetime
from typing import Any, Dict, List

from app.models import Ticket
from app import rules


def household_board(session, today: datetime.date) -> Dict[str, List[Dict[str, Any]]]:
    """Return the household board for *today*.

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
    # Fetch all tickets (both users). The query returns Ticket objects.
    tickets = session.query(Ticket).all()

    todo: List[Dict[str, Any]] = []
    in_progress: List[Dict[str, Any]] = []
    completed: List[Dict[str, Any]] = []

    # Define the 7‑day window for completed tickets (inclusive of today).
    window_start = today - datetime.timedelta(days=6)

    for t in tickets:
        # Ensure updated_at is treated as UTC for date comparison.
        updated = t.updated_at
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=datetime.timezone.utc)
        else:
            updated = updated.astimezone(datetime.timezone.utc)
        updated_date = updated.date()

        if t.status in {"open", "acknowledged"}:
            todo.append(rules.ticket_to_dict(t))
        elif t.status == "in_progress":
            in_progress.append(rules.ticket_to_dict(t))
        elif t.status in {"done", "closed"} and window_start <= updated_date <= today:
            completed.append(rules.ticket_to_dict(t))
        # other statuses are ignored

    # Sort todo and in_progress by oldest created_at first.
    def sort_by_created(item: Dict[str, Any]):
        # created_at is ISO‑8601 string; parse to datetime with UTC tz.
        dt = datetime.datetime.fromisoformat(item["created_at"]).replace(tzinfo=datetime.timezone.utc)
        return dt

    todo.sort(key=sort_by_created)
    in_progress.sort(key=sort_by_created)

    # Sort completed by newest updated_at first.
    def sort_by_updated_desc(item: Dict[str, Any]):
        dt = datetime.datetime.fromisoformat(item["updated_at"]).replace(tzinfo=datetime.timezone.utc)
        # Negate timestamp to get descending order.
        return -dt.timestamp()

    completed.sort(key=sort_by_updated_desc)

    return {"todo": todo, "in_progress": in_progress, "completed": completed}
