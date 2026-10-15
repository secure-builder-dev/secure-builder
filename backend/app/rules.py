from datetime import datetime, timezone
from typing import Dict, Optional

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