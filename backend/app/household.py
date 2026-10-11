from datetime import date, datetime, timezone, timedelta
from typing import Any

from sqlalchemy import select

from app.models import Ticket
from app.rules import _ticket_to_dict


def household_board(session: Any, today: date) -> dict[str, list[dict[str, Any]]]:
    """Return the household board with tickets from both users.
    
    Columns:
    - todo: tickets with status open or acknowledged, oldest created_at first
    - in_progress: tickets with status in_progress, oldest created_at first
    - completed: tickets with status done or closed whose updated_at date falls
      within the 7 days ending on today, newest updated_at first
    """
    # Todo: open or acknowledged, ordered by created_at oldest first
    todo_query = (
        session.execute(
            select(Ticket)
            .filter(Ticket.status.in_(("open", "acknowledged")))
            .order_by(Ticket.created_at.asc())
        ).scalars().all()
    )
    todo_list = [_ticket_to_dict(t) for t in todo_query]

    # In Progress: status in_progress, ordered by created_at oldest first
    in_progress_query = (
        session.execute(
            select(Ticket)
            .filter(Ticket.status == "in_progress")
            .order_by(Ticket.created_at.asc())
        ).scalars().all()
    )
    in_progress_list = [_ticket_to_dict(t) for t in in_progress_query]

    # Completed: done or closed, updated_at within 7 days ending today (inclusive)
    # Range: [today - 6 days, today] inclusive on both ends
    # So: updated_at >= start_of_day(today - 6 days) AND updated_at < start_of_day(today + 1 day)
    seven_days_ago = today - timedelta(days=6)
    completed_query = (
        session.execute(
            select(Ticket)
            .filter(Ticket.status.in_(("done", "closed")))
            .filter(
                Ticket.updated_at >= datetime.combine(seven_days_ago, datetime.min.time(), tzinfo=timezone.utc),
                Ticket.updated_at < datetime.combine(today + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
            )
            .order_by(Ticket.updated_at.desc())
        ).scalars().all()
    )
    completed_list = [_ticket_to_dict(t) for t in completed_query]

    return {
        "todo": todo_list,
        "in_progress": in_progress_list,
        "completed": completed_list,
    }
