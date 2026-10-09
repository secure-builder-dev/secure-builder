from datetime import datetime, date, timedelta, timezone
from sqlalchemy.orm import Session
from .models import Ticket

USERS = ('her', 'him')

def create_ticket(session: Session, filed_by: str, data: dict) -> dict:
    if filed_by not in USERS:
        raise ValueError('Invalid user')
    title = data.get('title', '').strip()
    if not title or len(title) < 1 or len(title) > 120:
        raise ValueError('Invalid title')
    details = data.get('details', '')
    if len(details) > 1000:
        raise ValueError('Details too long')
    priority = data.get('priority', 'normal')
    if priority not in ('low', 'normal', 'urgent'):
        raise ValueError('Invalid priority')
    due_str = data.get('due')
    due = None
    if due_str:
        try:
            due = datetime.strptime(due_str, '%Y-%m-%d').date()
        except ValueError:
            raise ValueError('Invalid due date')
    if set(data.keys()) - {'title', 'details', 'priority', 'due'}:
        raise ValueError('Invalid data keys')
    assigned_to = 'him' if filed_by == 'her' else 'her'
    ticket = Ticket(
        title=title,
        details=details,
        priority=priority,
        due=due,
        status='open',
        filed_by=filed_by,
        assigned_to=assigned_to,
        created_at=datetime.now(tz=timezone.utc),
        updated_at=datetime.now(tz=timezone.utc)
    )
    session.add(ticket)
    session.commit()
    session.refresh(ticket)
    return {
        'id': ticket.id,
        'title': ticket.title,
        'details': ticket.details,
        'priority': ticket.priority,
        'due': ticket.due.strftime('%Y-%m-%d') if ticket.due else None,
        'status': ticket.status,
        'filed_by': ticket.filed_by,
        'assigned_to': ticket.assigned_to,
        'created_at': ticket.created_at.isoformat(),
        'updated_at': ticket.updated_at.isoformat()
    }

def change_status(session: Session, ticket_id: int, user: str, new_status: str) -> dict:
    ticket = session.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket or (user != ticket.filed_by and user != ticket.assigned_to):
        raise LookupError('Ticket not found or user not a party')
    if new_status not in ('open', 'acknowledged', 'in_progress', 'done', 'closed'):
        raise ValueError('Invalid status')
    allowed_moves = {
        'open': {'acknowledged': 'assignee'},
        'acknowledged': {'in_progress': 'assignee'},
        'in_progress': {'done': 'assignee'},
        'done': {'closed': 'filer', 'open': 'filer'},
        'closed': {'open': 'filer'}
    }
    if ticket.status not in allowed_moves or new_status not in allowed_moves[ticket.status]:
        raise ValueError('Invalid move')
    if allowed_moves[ticket.status][new_status] == 'assignee' and user != ticket.assigned_to:
        raise PermissionError('User not allowed to make this move')
    if allowed_moves[ticket.status][new_status] == 'filer' and user != ticket.filed_by:
        raise PermissionError('User not allowed to make this move')
    ticket.status = new_status
    ticket.updated_at = datetime.now(tz=timezone.utc)
    session.commit()
    session.refresh(ticket)
    return {
        'id': ticket.id,
        'title': ticket.title,
        'details': ticket.details,
        'priority': ticket.priority,
        'due': ticket.due.strftime('%Y-%m-%d') if ticket.due else None,
        'status': ticket.status,
        'filed_by': ticket.filed_by,
        'assigned_to': ticket.assigned_to,
        'created_at': ticket.created_at.isoformat(),
        'updated_at': ticket.updated_at.isoformat()
    }

def dashboard(session: Session, user: str, today: date) -> dict:
    tickets = session.query(Ticket).filter(Ticket.assigned_to == user).all()
    todo = []
    in_progress = []
    completed = []
    for ticket in tickets:
        if ticket.status in ('open', 'acknowledged'):
            group = 2
            if ticket.priority == 'urgent' or (ticket.due and ticket.due < today):
                group = 0
            elif ticket.due and (today <= ticket.due <= today + timedelta(days=3)):
                group = 1
            todo.append({
                **ticket_to_dict(ticket),
                'group': group
            })
        elif ticket.status == 'in_progress':
            group = 2
            if ticket.priority == 'urgent' or (ticket.due and ticket.due < today):
                group = 0
            elif ticket.due and (today <= ticket.due <= today + timedelta(days=3)):
                group = 1
            in_progress.append({
                **ticket_to_dict(ticket),
                'group': group
            })
        elif ticket.status in ('done', 'closed'):
            if today - ticket.updated_at.date() <= timedelta(days=7):
                completed.append(ticket_to_dict(ticket))
    todo.sort(key=lambda x: (x['group'], datetime.strptime(x['due'], '%Y-%m-%d').date() if x['due'] else date.max, x['created_at']))
    in_progress.sort(key=lambda x: (x['group'], datetime.strptime(x['due'], '%Y-%m-%d').date() if x['due'] else date.max, x['created_at']))
    completed.sort(key=lambda x: x['updated_at'], reverse=True)
    return {
        'todo': todo,
        'in_progress': in_progress,
        'completed': completed
    }

def filed(session: Session, user: str) -> list:
    tickets = session.query(Ticket).filter(Ticket.filed_by == user).order_by(Ticket.created_at.desc()).all()
    return [ticket_to_dict(ticket) for ticket in tickets]

def ticket_to_dict(ticket: Ticket) -> dict:
    return {
        'id': ticket.id,
        'title': ticket.title,
        'details': ticket.details,
        'priority': ticket.priority,
        'due': ticket.due.strftime('%Y-%m-%d') if ticket.due else None,
        'status': ticket.status,
        'filed_by': ticket.filed_by,
        'assigned_to': ticket.assigned_to,
        'created_at': ticket.created_at.isoformat(),
        'updated_at': ticket.updated_at.isoformat()
    }