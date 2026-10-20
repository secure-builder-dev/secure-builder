import datetime as dt

from app.models import Ticket
from app.rules import ticket_to_dict


def _matches(ticket, q=None, priority=None, assigned_to=None):
    if q:
        needle = q.lower()
        if needle not in ticket.title.lower() and needle not in (ticket.details or "").lower():
            return False
    if priority and ticket.priority != priority:
        return False
    if assigned_to and ticket.assigned_to != assigned_to:
        return False
    return True


def household_board(session, today, q=None, priority=None, assigned_to=None):
    tickets = [t for t in session.query(Ticket).all() if _matches(t, q, priority, assigned_to)]
    todo = [t for t in tickets if t.status in ("open", "acknowledged")]
    in_progress = [t for t in tickets if t.status == "in_progress"]
    window_start = today - dt.timedelta(days=6)
    completed = [
        t for t in tickets
        if t.status in ("done", "closed") and window_start <= t.updated_at.date() <= today
    ]
    todo.sort(key=lambda t: t.created_at)
    in_progress.sort(key=lambda t: t.created_at)
    completed.sort(key=lambda t: t.updated_at, reverse=True)
    return {
        "todo": [ticket_to_dict(t) for t in todo],
        "in_progress": [ticket_to_dict(t) for t in in_progress],
        "completed": [ticket_to_dict(t) for t in completed],
    }


def summary(session, user, today):
    tickets = session.query(Ticket).filter(Ticket.assigned_to == user).all()
    open_tickets = [t for t in tickets if t.status not in ("done", "closed")]
    overdue = sum(1 for t in open_tickets if t.due is not None and t.due < today)
    due_today = sum(1 for t in open_tickets if t.due == today)
    return {"overdue": overdue, "due_today": due_today, "open": len(open_tickets)}
