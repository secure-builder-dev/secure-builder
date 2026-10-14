from datetime import datetime, timezone, date
from typing import Any

USERS = ('her', 'him')

VALID_PRIORITIES = ('low', 'normal', 'urgent')
ALLOWED_DATA_KEYS = {'title', 'details', 'priority', 'due'}


def ticket_to_dict(ticket: Any) -> dict:
    """Convert a Ticket model instance to a plain dict.
    
    - due: YYYY-MM-DD string or None
    - created_at, updated_at: ISO-8601 strings (datetime.isoformat())
    """
    result = {
        'id': ticket.id,
        'title': ticket.title,
        'details': ticket.details,
        'priority': ticket.priority,
        'status': ticket.status,
        'filed_by': ticket.filed_by,
        'assigned_to': ticket.assigned_to,
    }
    
    # Format due date
    if ticket.due is not None:
        result['due'] = ticket.due.isoformat()
    else:
        result['due'] = None
    
    # Format timestamps as ISO-8601
    result['created_at'] = ticket.created_at.isoformat()
    result['updated_at'] = ticket.updated_at.isoformat()
    
    return result


def _validate_title(value: Any) -> str:
    """Validate and process title field.
    
    Returns stripped title if valid, raises ValueError otherwise.
    """
    if not isinstance(value, str):
        raise ValueError("title must be a string")
    
    stripped = value.strip()
    
    if len(stripped) < 1:
        raise ValueError("title must be at least 1 character after stripping")
    
    if len(stripped) > 120:
        raise ValueError("title must be at most 120 characters after stripping")
    
    return stripped


def _validate_details(value: Any) -> str:
    """Validate and process details field.
    
    Returns value if valid, raises ValueError otherwise.
    Default is empty string.
    """
    if value is None:
        return ""
    
    if not isinstance(value, str):
        raise ValueError("details must be a string")
    
    if len(value) > 1000:
        raise ValueError("details must be at most 1000 characters")
    
    return value


def _validate_priority(value: Any) -> str:
    """Validate and process priority field.
    
    Returns value if valid, raises ValueError otherwise.
    Default is 'normal'.
    """
    if value is None:
        return 'normal'
    
    if not isinstance(value, str):
        raise ValueError("priority must be a string")
    
    if value not in VALID_PRIORITIES:
        raise ValueError(f"priority must be one of {VALID_PRIORITIES}")
    
    return value


def _validate_due(value: Any) -> date | None:
    """Validate and process due field.
    
    Returns date object if valid, None if value is None, raises ValueError otherwise.
    Default is None.
    """
    if value is None:
        return None
    
    if not isinstance(value, str):
        raise ValueError("due must be a string in YYYY-MM-DD format or None")
    
    try:
        parsed_date = date.fromisoformat(value)
        # Verify it's a real date by checking the components match
        reconstructed = f"{parsed_date.year:04d}-{parsed_date.month:02d}-{parsed_date.day:02d}"
        if reconstructed != value:
            raise ValueError("due must be in YYYY-MM-DD format")
        return parsed_date
    except ValueError:
        raise ValueError("due must be a valid date in YYYY-MM-DD format")


def create_ticket(session, filed_by: str, data: dict) -> dict:
    """Create a new ticket.
    
    Args:
        session: Database session
        filed_by: User creating the ticket (must be in USERS)
        data: Dict with optional keys title, details, priority, due
              title is required
    
    Returns:
        ticket_to_dict of the created ticket
    
    Raises:
        ValueError: If filed_by not in USERS, data has invalid keys,
                   or any field validation fails
    """
    from app.models import Ticket
    
    # Validate filed_by
    if filed_by not in USERS:
        raise ValueError(f"filed_by must be one of {USERS}")
    
    # Validate data is a dict
    if not isinstance(data, dict):
        raise ValueError("data must be a dict")
    
    # Check for invalid keys
    invalid_keys = set(data.keys()) - ALLOWED_DATA_KEYS
    if invalid_keys:
        raise ValueError(f"data contains invalid keys: {invalid_keys}")
    
    # Validate and process fields
    title = _validate_title(data.get('title'))
    details = _validate_details(data.get('details'))
    priority = _validate_priority(data.get('priority'))
    due_date = _validate_due(data.get('due'))
    
    # Determine assigned_to (the other user)
    assigned_to = 'him' if filed_by == 'her' else 'her'
    
    # Set current time
    now = datetime.now(timezone.utc)
    
    # Create ticket instance
    ticket = Ticket(
        title=title,
        details=details,
        priority=priority,
        due=due_date,
        status='open',
        filed_by=filed_by,
        assigned_to=assigned_to,
        created_at=now,
        updated_at=now
    )
    
    # Add to session and commit
    session.add(ticket)
    session.commit()
    
    return ticket_to_dict(ticket)
