from datetime import datetime, date, timedelta, timezone
from typing import Any
from sqlalchemy import select
from app.models import Ticket
from app.rules import _ticket_to_dict


def household_board(session: Any, today: date) -> dict[str, list[dict[str, Any]]]:
    """Get the household board showing all tickets from both users.
    
    Args:
        session: SQLAlchemy session
        today: The reference date for the board
        
    Returns:
        Dict with 'todo', 'in_progress', and 'completed' lists
    """
    # Get tickets with status open or acknowledged (todo)
    todo_query = (
        select(Ticket)
        .where(Ticket.status.in_(("open", "acknowledged")))
        .order_by(Ticket.created_at.asc())
    )
    todo_tickets = session.execute(todo_query).scalars().all()
    
    # Get tickets with status in_progress
    in_progress_query = (
        select(Ticket)
        .where(Ticket.status == "in_progress")
        .order_by(Ticket.created_at.asc())
    )
    in_progress_tickets = session.execute(in_progress_query).scalars().all()
    
    # Get completed tickets (done or closed) within 7 days ending today
    # "within the 7 days ending on today" means: (today - 7 days, today] exclusive start, inclusive end
    seven_days_ago = today - timedelta(days=7)
    completed_query = (
        select(Ticket)
        .where(Ticket.status.in_(("done", "closed")))
        .where(Ticket.updated_at > datetime.combine(seven_days_ago, datetime.min.time(), tzinfo=timezone.utc))
        .where(Ticket.updated_at < datetime.combine(today + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc))
        .order_by(Ticket.updated_at.desc())
    )
    completed_tickets = session.execute(completed_query).scalars().all()
    
    # Convert to dicts
    todo_list = [_ticket_to_dict(t) for t in todo_tickets]
    in_progress_list = [_ticket_to_dict(t) for t in in_progress_tickets]
    completed_list = [_ticket_to_dict(t) for t in completed_tickets]
    
    return {
        "todo": todo_list,
        "in_progress": in_progress_list,
        "completed": completed_list,
    }
