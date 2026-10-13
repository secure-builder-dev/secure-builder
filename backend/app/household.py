from datetime import date, timedelta, timezone

from app.models import Ticket
from app.rules import ticket_to_dict


def household_board(session, today: date) -> dict:
    """
    Get the household board with all tickets from both users.
    
    Args:
        session: Database session
        today: The current date (UTC)
    
    Returns:
        Dict with 'todo', 'in_progress', 'completed' lists of ticket dicts.
        No 'group' key on any ticket.
    """
    # Get all tickets from both users
    all_tickets = session.query(Ticket).all()
    
    todo = []
    in_progress = []
    completed = []
    
    # Calculate the 7-day window for completed (today + 6 days before)
    window_start = today - timedelta(days=6)
    
    for ticket in all_tickets:
        if ticket.status in ("open", "acknowledged"):
            # Todo tickets
            todo.append(ticket_to_dict(ticket))
        elif ticket.status == "in_progress":
            # In progress tickets
            in_progress.append(ticket_to_dict(ticket))
        elif ticket.status in ("done", "closed"):
            # Check if within the 7-day window based on updated_at date
            updated_at = ticket.updated_at
            if not updated_at.tzinfo:
                updated_at = updated_at.replace(tzinfo=timezone.utc)
            updated_date = updated_at.date()
            if window_start <= updated_date <= today:
                completed.append(ticket_to_dict(ticket))
    
    # Sort todo by created_at oldest first
    todo.sort(key=lambda t: t["created_at"])
    
    # Sort in_progress by created_at oldest first
    in_progress.sort(key=lambda t: t["created_at"])
    
    # Sort completed by updated_at newest first
    completed.sort(key=lambda t: t["updated_at"], reverse=True)
    
    return {
        "todo": todo,
        "in_progress": in_progress,
        "completed": completed
    }
