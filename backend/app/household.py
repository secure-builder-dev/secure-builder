from sqlalchemy.orm import Session
from datetime import date, datetime, timedelta, timezone
from .models import Ticket
from .rules import ticket_to_dict

def household_board(session: Session, today: date) -> dict:
    tickets = session.query(Ticket).all()
    todo = []
    in_progress = []
    completed = []
    for ticket in tickets:
        if ticket.status in ('open', 'acknowledged'):
            todo.append(ticket_to_dict(ticket))
        elif ticket.status == 'in_progress':
            in_progress.append(ticket_to_dict(ticket))
        elif ticket.status in ('done', 'closed') and today - ticket.updated_at.date() <= timedelta(days=7):
            completed.append(ticket_to_dict(ticket))
    todo.sort(key=lambda x: x['created_at'])
    in_progress.sort(key=lambda x: x['created_at'])
    completed.sort(key=lambda x: x['updated_at'], reverse=True)
    return {'todo': todo, 'in_progress': in_progress, 'completed': completed}