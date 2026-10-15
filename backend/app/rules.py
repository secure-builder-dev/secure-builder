from datetime import datetime, timezone
from typing import Dict, List, Optional
from app.models import Ticket

USERS = ('her', 'him')


def ticket_to_dict(ticket) -> Dict:
    """Convert a Ticket object to a plain dict with every column."""
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
        'updated_at': ticket.updated_at.isoformat(),
    }


def create_ticket(session, filed_by: str, data: Dict) -> Dict:
    """Create a new ticket with validation."""
    # Validate filed_by
    if filed_by not in USERS:
        raise ValueError(f"filed_by must be one of {USERS}")

    # Validate data keys
    valid_keys = {'title', 'details', 'priority', 'due'}
    if not valid_keys.issuperset(data.keys()):
        raise ValueError(f"data can only contain keys: {valid_keys}")

    # Validate title
    title = data.get('title')
    if title is None:
        raise ValueError("title is required")
    if not isinstance(title, str):
        raise ValueError("title must be a string")
    stripped_title = title.strip()
    if len(stripped_title) < 1 or len(stripped_title) > 120:
        raise ValueError("title must be 1-120 characters after stripping")

    # Validate details
    details = data.get('details', '')
    if not isinstance(details, str):
        raise ValueError("details must be a string")
    if len(details) > 1000:
        raise ValueError("details must be at most 1000 characters")

    # Validate priority
    priority = data.get('priority', 'normal')
    if priority not in {'low', 'normal', 'urgent'}:
        raise ValueError("priority must be one of 'low', 'normal', 'urgent'")

    # Validate due
    due = data.get('due')
    if due is not None:
        if not isinstance(due, str):
            raise ValueError("due must be a string in YYYY-MM-DD format or None")
        try:
            datetime.strptime(due, '%Y-%m-%d')
        except ValueError:
            raise ValueError("due must be a valid date in YYYY-MM-DD format")

    # Determine assigned_to (the other user)
    assigned_to = 'him' if filed_by == 'her' else 'her'

    # Create the ticket
    now = datetime.now(timezone.utc)
    ticket = type('Ticket', (), {
        'id': None,
        'title': stripped_title,
        'details': details,
        'priority': priority,
        'due': datetime.strptime(due, '%Y-%m-%d').date() if due else None,
        'status': 'open',
        'filed_by': filed_by,
        'assigned_to': assigned_to,
        'created_at': now,
        'updated_at': now,
    })
    session.add(ticket)
    session.commit()

    return ticket_to_dict(ticket)


def change_status(session, ticket_id: int, user: str, new_status: str) -> Dict:
    """Change the status of a ticket according to the status table."""
    # Status table: from -> to -> who
    status_table = {
        'open': {'acknowledged': 'assignee'},
        'acknowledged': {'in_progress': 'assignee'},
        'in_progress': {'done': 'assignee'},
        'done': {'closed': 'filer', 'open': 'filer'},
        'closed': {'open': 'filer'},
    }

    # Get the ticket
    ticket = session.query(Ticket).filter(Ticket.id == ticket_id).first()
    if ticket is None:
        raise LookupError("Ticket not found")

    # Check if user is a party (filer or assignee)
    if user not in (ticket.filed_by, ticket.assigned_to):
        raise LookupError("User is not a party to this ticket")

    # Validate new_status
    valid_statuses = {'open', 'acknowledged', 'in_progress', 'done', 'closed'}
    if new_status not in valid_statuses:
        raise ValueError("Invalid status")

    # Check if the move is in the table
    if ticket.status not in status_table or new_status not in status_table[ticket.status]:
        raise ValueError("Invalid transition")

    # Check if the user has permission for this move
    required_party = status_table[ticket.status][new_status]
    if required_party == 'assignee' and user != ticket.assigned_to:
        raise PermissionError("Only the assignee can make this move")
    if required_party == 'filer' and user != ticket.filed_by:
        raise PermissionError("Only the filer can make this move")

    # Update the ticket
    ticket.status = new_status
    ticket.updated_at = datetime.now(timezone.utc)
    session.commit()

    return ticket_to_dict(ticket)


def dashboard(session, user: str, today: datetime.date) -> Dict:
    """Return the personal dashboard for a user."""
    # Get all tickets assigned to the user
    tickets = session.query(Ticket).filter(Ticket.assigned_to == user).all()
    
    todo = []
    in_progress = []
    completed = []
    
    for ticket in tickets:
        ticket_dict = ticket_to_dict(ticket)
        
        if ticket.status in ('open', 'acknowledged'):
            # Determine group
            if ticket.priority == 'urgent' or (ticket.due and ticket.due < today):
                group = 0
            elif ticket.due and (ticket.due <= today or (today <= ticket.due <= today + datetime.timedelta(days=3))):
                group = 1
            else:
                group = 2
            ticket_dict['group'] = group
            todo.append(ticket_dict)
        elif ticket.status == 'in_progress':
            # Determine group
            if ticket.priority == 'urgent' or (ticket.due and ticket.due < today):
                group = 0
            elif ticket.due and (ticket.due <= today or (today <= ticket.due <= today + datetime.timedelta(days=3))):
                group = 1
            else:
                group = 2
            ticket_dict['group'] = group
            in_progress.append(ticket_dict)
        elif ticket.status in ('done', 'closed'):
            # Check if updated_at is within the last 7 days
            updated_date = ticket.updated_at.date()
            if today - datetime.timedelta(days=6) <= updated_date <= today:
                completed.append(ticket_dict)
    
    # Sort todo and in_progress by group, then due date, then created_at
    def sort_key(ticket_dict):
        group = ticket_dict['group']
        due = ticket_dict['due']
        created_at = ticket_dict['created_at']
        
        # Convert due to date for comparison
        due_date = datetime.strptime(due, '%Y-%m-%d').date() if due else None
        
        return (group, due_date, created_at)
    
    todo.sort(key=sort_key)
    in_progress.sort(key=sort_key)
    
    # Sort completed by updated_at newest first
    completed.sort(key=lambda x: x['updated_at'], reverse=True)
    
    return {
        'todo': todo,
        'in_progress': in_progress,
        'completed': completed,
    }


def filed(session, user: str) -> List[Dict]:
    """Return all tickets filed by a user, newest first."""
    tickets = session.query(Ticket).filter(Ticket.filed_by == user).order_by(Ticket.created_at.desc()).all()
    return [ticket_to_dict(ticket) for ticket in tickets]
