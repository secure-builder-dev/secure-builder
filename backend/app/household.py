import datetime as dt
from app.models import Ticket
from app.rules import ticket_to_dict


def household_board(session, today: dt.date):
    """Return the household board for *both* users.

    The result is a dict with keys ``todo``, ``in_progress`` and ``completed``.
    ``todo`` contains tickets with status ``open`` or ``acknowledged``.
    ``in_progress`` contains tickets with status ``in_progress``.
    ``completed`` contains tickets with status ``done`` or ``closed`` whose
    ``updated_at`` falls within the 7‑day window ending on *today* (today and the
    six previous days).

    ``todo`` and ``in_progress`` tickets are ordered by ``created_at`` oldest
    first, ignoring priority or due date. ``completed`` tickets are ordered by
    ``updated_at`` newest first. No ticket dict includes a ``group`` key.
    """
    # Fetch all tickets (both users).
    tickets = session.query(Ticket).all()

    todo = []
    in_progress = []
    completed = []

    for t in tickets:
        td = ticket_to_dict(t)
        if t.status in {"open", "acknowledged"}:
            todo.append(td)
        elif t.status == "in_progress":
            in_progress.append(td)
        elif t.status in {"done", "closed"}:
            # Check completed window: updated_at date within today and 6 days before.
            upd_date = t.updated_at.date()
            if 0 <= (today - upd_date).days <= 6:
                completed.append(td)
        # other statuses are ignored (should not exist)

    # Sort todo and in_progress by created_at oldest first.
    def created_key(item):
        # Parse ISO string to datetime with timezone awareness.
        return dt.datetime.fromisoformat(item["created_at"]).replace(tzinfo=dt.timezone.utc)

    todo.sort(key=created_key)
    in_progress.sort(key=created_key)

    # Sort completed by updated_at newest first.
    completed.sort(
        key=lambda i: dt.datetime.fromisoformat(i["updated_at"]).replace(tzinfo=dt.timezone.utc),
        reverse=True,
    )

    return {"todo": todo, "in_progress": in_progress, "completed": completed}
