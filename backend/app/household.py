from datetime import date, timedelta
from app.models import Ticket
from app.rules import ticket_to_dict
from sqlalchemy import select


def household_board(session, today: date) -> dict:
    """Get the household board with all tickets from both users.
    
    Args:
        session: Database session
        today: The reference date for the completed window
    
    Returns:
        Dict with keys 'todo', 'in_progress', 'completed', each a list of
        ticket_to_dict dicts (no 'group' key).
    """
    # Get all tickets from both users
    stmt = select(Ticket)
    tickets = session.execute(stmt).scalars().all()
    
    todo_items = []
    in_progress_items = []
    completed_items = []
    
    # Calculate the 7-day window for completed (today + 6 days before)
    window_start = today - timedelta(days=6)
    
    for ticket in tickets:
        if ticket.status in ('open', 'acknowledged'):
            # Todo column
            ticket_dict = ticket_to_dict(ticket)
            todo_items.append(ticket_dict)
        elif ticket.status == 'in_progress':
            # In progress column
            ticket_dict = ticket_to_dict(ticket)
            in_progress_items.append(ticket_dict)
        elif ticket.status in ('done', 'closed'):
            # Check if updated_at is within the 7-day window
            ticket_updated_date = ticket.updated_at.date()
            if window_start <= ticket_updated_date <= today:
                completed_items.append(ticket)
    
    # Sort todo and in_progress by created_at oldest first
    todo_items.sort(key=lambda t: t['created_at'])
    in_progress_items.sort(key=lambda t: t['created_at'])
    
    # Sort completed by updated_at newest first
    completed_items.sort(key=lambda t: t.updated_at, reverse=True)
    completed = [ticket_to_dict(t) for t in completed_items]
    
    return {
        'todo': todo_items,
        'in_progress': in_progress_items,
        'completed': completed
    }
