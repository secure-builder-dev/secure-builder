from datetime import datetime, date, timedelta, timezone
from app.models import Ticket


def household_board(session, today):
    """
    Returns a household board with tickets from both users.
    
    Args:
        session: SQLAlchemy session
        today: datetime.date for the current day
    
    Returns:
        dict: {'todo': [...], 'in_progress': [...], 'completed': [...]} where each ticket
              is represented as a dict from ticket_to_dict
    """
    # Get all tickets from both users
    tickets = session.query(Ticket).all()
    
    todo = []
    in_progress = []
    completed = []
    
    for ticket in tickets:
        # Convert ticket to dict
        ticket_dict = {
            "id": ticket.id,
            "title": ticket.title,
            "details": ticket.details,
            "priority": ticket.priority,
            "due": ticket.due.strftime("%Y-%m-%d") if ticket.due else None,
            "status": ticket.status,
            "filed_by": ticket.filed_by,
            "assigned_to": ticket.assigned_to,
            "created_at": ticket.created_at.isoformat(),
            "updated_at": ticket.updated_at.isoformat()
        }
        
        if ticket.status in ("open", "acknowledged"):
            todo.append(ticket_dict)
        elif ticket.status == "in_progress":
            in_progress.append(ticket_dict)
        elif ticket.status in ("done", "closed"):
            # Check if updated_at is within 7 days ending today
            updated_date = ticket.updated_at.date()
            if updated_date >= today - timedelta(days=7):
                completed.append(ticket_dict)
    
    # Sort todo and in_progress by oldest created_at first
    todo.sort(key=lambda x: x["created_at"])
    in_progress.sort(key=lambda x: x["created_at"])
    
    # Sort completed by newest updated_at first
    completed.sort(key=lambda x: x["updated_at"], reverse=True)
    
    return {
        "todo": todo,
        "in_progress": in_progress,
        "completed": completed
    }
