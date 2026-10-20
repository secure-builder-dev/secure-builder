import datetime as dt
from app.models import Ticket
from app.rules import ticket_to_dict


def household_board(session, today: dt.date, q=None, priority=None, assigned_to=None):
    """Return the household board for *both* users, optionally filtered.

    Parameters
    ----------
    session: SQLAlchemy session.
    today: date used for the completed‑window calculation.
    q: optional case‑insensitive substring to match in title or details.
    priority: optional priority filter ("low", "normal", "urgent").
    assigned_to: optional filter for the ``assigned_to`` field ("her" or "him").

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

    # Normalise filter values: treat None or empty string as no filter.
    q_val = None if q is None or q == "" else str(q).lower()
    priority_val = None if priority is None or priority == "" else str(priority)
    assigned_to_val = None if assigned_to is None or assigned_to == "" else str(assigned_to)

    todo = []
    in_progress = []
    completed = []

    for t in tickets:
        # Apply filters early – if any filter does not match, skip the ticket.
        if q_val is not None:
            if q_val not in t.title.lower() and q_val not in (t.details or "").lower():
                continue
        if priority_val is not None and t.priority != priority_val:
            continue
        if assigned_to_val is not None and t.assigned_to != assigned_to_val:
            continue

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


def summary(session, user: str, today: dt.date):
    """Return a summary dict for *user*.

    The dict contains ``overdue``, ``due_today`` and ``open`` counts over the
    tickets assigned to ``user`` whose status is not ``done`` or ``closed``.
    ``overdue`` counts tickets with a due date before *today*.
    ``due_today`` counts tickets with a due date equal to *today*.
    ``open`` counts all such tickets regardless of due date.
    """
    tickets = session.query(Ticket).filter(Ticket.assigned_to == user).all()
    overdue = 0
    due_today = 0
    open_cnt = 0
    for t in tickets:
        if t.status in {"done", "closed"}:
            continue
        open_cnt += 1
        if t.due is not None:
            if t.due < today:
                overdue += 1
            elif t.due == today:
                due_today += 1
    return {"overdue": overdue, "due_today": due_today, "open": open_cnt}
