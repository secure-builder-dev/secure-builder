from datetime import date, timedelta
from sqlalchemy.orm import Session
from app.models import Ticket


def ticket_to_dict(ticket: Ticket) -> dict:
    """Convert a Ticket model to a dict as per rules.ticket_to_dict"""
    return {
        "id": ticket.id,
        "title": ticket.title,
        "details": ticket.details,
        "priority": ticket.priority,
        "due": ticket.due.isoformat() if ticket.due else None,
        "status": ticket.status,
        "filed_by": ticket.filed_by,
        "assigned_to": ticket.assigned_to,
        "created_at": ticket.created_at.isoformat(),
        "updated_at": ticket.updated_at.isoformat()
    }


def household_board(session: Session, today: date) -> dict:
    """
    Returns a household board with tickets from both users.
    
    Structure:
    {
        'todo': [...],           # open or acknowledged, oldest created_at first
        'in_progress': [...],    # in_progress, oldest created_at first
        'completed': [...]       # done or closed within 7 days ending today, newest updated_at first
    }
    """
    todo = []
    in_progress = []
    completed = []
    
    # Get all tickets from both users
    tickets = session.query(Ticket).all()
    
    for ticket in tickets:
        ticket_dict = ticket_to_dict(ticket)
        
        if ticket.status in ("open", "acknowledged"):
            todo.append(ticket_dict)
        elif ticket.status == "in_progress":
            in_progress.append(ticket_dict)
        elif ticket.status in ("done", "closed"):
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
