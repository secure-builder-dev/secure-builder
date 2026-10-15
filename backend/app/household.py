from datetime import datetime, date, timezone, timedelta
from typing import Dict, List
from app.models import Ticket
from app.rules import ticket_to_dict


def household_board(session, today: date) -> Dict:
    """Return the household board with all tickets from both users."""
    # Get all tickets from both users
    tickets = session.query(Ticket).all()
    
    todo = []
    in_progress = []
    completed = []
    
    for ticket in tickets:
        ticket_dict = ticket_to_dict(ticket)
        
        if ticket.status in ('open', 'acknowledged'):
            todo.append(ticket_dict)
        elif ticket.status == 'in_progress':
            in_progress.append(ticket_dict)
        elif ticket.status in ('done', 'closed'):
            # Check if updated_at is within the last 7 days
            updated_date = ticket.updated_at.date()
            if today - timedelta(days=6) <= updated_date <= today:
                completed.append(ticket_dict)
    
    # Sort todo and in_progress by created_at oldest first
    todo.sort(key=lambda x: x['created_at'])
    in_progress.sort(key=lambda x: x['created_at'])
    
    # Sort completed by updated_at newest first
    completed.sort(key=lambda x: x['updated_at'], reverse=True)
    
    return {
        'todo': todo,
        'in_progress': in_progress,
        'completed': completed,
    }
