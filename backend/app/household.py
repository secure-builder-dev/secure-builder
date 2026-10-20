import datetime as dt

from app.models import Ticket
from app.rules import ticket_to_dict


def household_board(session, today):
    tickets = session.query(Ticket).all()
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
