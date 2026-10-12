from datetime import date, timedelta
from typing import Any

from sqlalchemy import select

from app.models import Ticket
from app.rules import ticket_to_dict


def household_board(session, today: date) -> dict[str, list[dict[str, Any]]]:
    """Return the household board with every ticket of both users.
    
    Args:
        session: Database session
        today: The reference date for the completed window
    
    Returns:
        Dict with keys 'todo', 'in_progress', 'completed', each a list of ticket dicts.
        todo and in_progress are ordered by created_at oldest first (no group key).
        completed is ordered by updated_at newest first.
    """
    # Get all tickets from both users
    stmt = select(Ticket).order_by(Ticket.created_at)
    tickets = session.execute(stmt).scalars().all()
    
    todo: list[dict[str, Any]] = []
    in_progress: list[dict[str, Any]] = []
    completed: list[dict[str, Any]] = []
    
    # Completed window: today and the 6 days before (7 days ending today)
    window_start = today - timedelta(days=6)
    
    for ticket in tickets:
        tdict = ticket_to_dict(ticket)
        status = ticket.status
        
        if status in ("open", "acknowledged"):
            todo.append(tdict)
        elif status == "in_progress":
            in_progress.append(tdict)
        elif status in ("done", "closed"):
            # Check if updated_at is within the completed window
            update_date = ticket.updated_at.date()
            if window_start <= update_date <= today:
                completed.append(tdict)
    
    # Sort completed: newest updated_at first
    completed.sort(key=lambda t: t["updated_at"], reverse=True)
    
    return {
        "todo": todo,
        "in_progress": in_progress,
        "completed": completed,
    }
