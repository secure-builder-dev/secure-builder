from datetime import datetime, timezone, date, timedelta
from typing import Any

USERS = ('her', 'him')

VALID_PRIORITIES = ('low', 'normal', 'urgent')
ALLOWED_DATA_KEYS = {'title', 'details', 'priority', 'due'}


class NotEditable(Exception):
    """Raised when a ticket cannot be edited (status is not open or acknowledged)."""
    pass


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
    
    # Format timestamps as ISO-8601 in UTC
    result['created_at'] = ticket.created_at.astimezone(timezone.utc).isoformat()
    result['updated_at'] = ticket.updated_at.astimezone(timezone.utc).isoformat()
    
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


# Status transition table: (from_status, to_status) -> required_party
# 'filer' means the user who filed the ticket
# 'assignee' means the user the ticket is assigned to
STATUS_TRANSITIONS = {
    ('open', 'acknowledged'): 'assignee',
    ('acknowledged', 'in_progress'): 'assignee',
    ('in_progress', 'done'): 'assignee',
    ('done', 'closed'): 'filer',
    ('done', 'open'): 'filer',
    ('closed', 'open'): 'filer',
}

VALID_STATUSES = {'open', 'acknowledged', 'in_progress', 'done', 'closed'}


def change_status(session, ticket_id: int, user: str, new_status: str) -> dict:
    """Change the status of a ticket according to the status transition table.
    
    Args:
        session: Database session
        ticket_id: ID of the ticket to update
        user: User attempting the change (must be filer or assignee)
        new_status: Target status
    
    Returns:
        ticket_to_dict of the updated ticket
    
    Raises:
        LookupError: If ticket does not exist or user is not a party
        ValueError: If new_status is invalid or transition is not allowed
        PermissionError: If user is not the required party for this transition
    """
    from app.models import Ticket
    from app.activity import record_event
    
    # Check 1: LookupError - ticket must exist and user must be a party
    ticket = session.get(Ticket, ticket_id)
    if ticket is None:
        raise LookupError(f"Ticket {ticket_id} not found")
    
    if user != ticket.filed_by and user != ticket.assigned_to:
        raise LookupError(f"User '{user}' is not a party to ticket {ticket_id}")
    
    # Check 2: ValueError - new_status must be valid
    if new_status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {new_status}")
    
    # Check 3: ValueError - transition must be in the table (including same-status)
    current_status = ticket.status
    if current_status == new_status:
        raise ValueError("Cannot change status to the same status")
    
    transition_key = (current_status, new_status)
    if transition_key not in STATUS_TRANSITIONS:
        raise ValueError(f"Invalid transition from {current_status} to {new_status}")
    
    # Check 4: PermissionError - user must be the required party
    required_party = STATUS_TRANSITIONS[transition_key]
    expected_user = ticket.filed_by if required_party == 'filer' else ticket.assigned_to
    
    if user != expected_user:
        raise PermissionError(f"User '{user}' is not authorized for this transition")
    
    # All checks passed - perform the update and record event
    now = datetime.now(timezone.utc)
    ticket.status = new_status
    ticket.updated_at = now
    
    # Record the status change event (not committed yet)
    record_event(session, ticket, user, 'status', from_status=current_status, to_status=new_status)
    
    session.commit()
    
    return ticket_to_dict(ticket)


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
    from app.activity import record_event
    
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
    
    # Add ticket to session
    session.add(ticket)
    session.flush()  # Get the ticket ID before recording event
    
    # Record the 'filed' event (not committed yet)
    record_event(session, ticket, filed_by, 'filed', from_status=None, to_status='open')
    
    session.commit()
    
    return ticket_to_dict(ticket)


def _compute_group(priority: str, due: date | None, today: date) -> int:
    """Compute the group value for a ticket.
    
    Group 0: priority is 'urgent' OR due is before today
    Group 1: due is today or within 3 days after today
    Group 2: otherwise (including no due date)
    """
    # Group 0: urgent priority or due before today
    if priority == 'urgent':
        return 0
    if due is not None and due < today:
        return 0
    
    # Group 1: due today or within 3 days after today
    if due is not None:
        days_until_due = (due - today).days
        if 0 <= days_until_due <= 3:
            return 1
    
    # Group 2: everything else
    return 2


def _sort_key_for_active(ticket, group: int):
    """Sort key for todo and in_progress tickets.
    
    Order by: group, then due date (none last), then created_at oldest first.
    """
    # For due date sorting: None should come last
    # We use a tuple: (has_no_due, due_date) where has_no_due is 1 for None, 0 otherwise
    if ticket.due is None:
        due_sort = (1, date.max)
    else:
        due_sort = (0, ticket.due)
    
    return (group, due_sort, ticket.created_at)


def dashboard(session, user: str, today: date) -> dict:
    """Get the personal board for a user.
    
    Args:
        session: Database session
        user: The user whose board to retrieve ('her' or 'him')
        today: The reference date for grouping and completed window
    
    Returns:
        Dict with keys 'todo', 'in_progress', 'completed', each a list of
        ticket_to_dict dicts (with extra 'group' key for todo/in_progress).
    """
    from app.models import Ticket
    from sqlalchemy import select, and_, or_
    
    # Get all tickets assigned to this user
    stmt = select(Ticket).where(Ticket.assigned_to == user)
    tickets = session.execute(stmt).scalars().all()
    
    todo_items = []
    in_progress_items = []
    completed_items = []
    
    # Calculate the 7-day window for completed (today + 6 days before)
    window_start = today - timedelta(days=6)
    
    for ticket in tickets:
        if ticket.status in ('open', 'acknowledged'):
            # Todo column
            group = _compute_group(ticket.priority, ticket.due, today)
            ticket_dict = ticket_to_dict(ticket)
            ticket_dict['group'] = group
            todo_items.append((ticket, ticket_dict))
        elif ticket.status == 'in_progress':
            # In progress column
            group = _compute_group(ticket.priority, ticket.due, today)
            ticket_dict = ticket_to_dict(ticket)
            ticket_dict['group'] = group
            in_progress_items.append((ticket, ticket_dict))
        elif ticket.status in ('done', 'closed'):
            # Check if updated_at is within the 7-day window
            ticket_updated_date = ticket.updated_at.date()
            if window_start <= ticket_updated_date <= today:
                completed_items.append(ticket)
    
    # Sort todo and in_progress by group, then due (none last), then created_at
    todo_items.sort(key=lambda x: _sort_key_for_active(x[0], x[1]['group']))
    in_progress_items.sort(key=lambda x: _sort_key_for_active(x[0], x[1]['group']))
    
    # Extract just the dicts
    todo = [item_dict for _, item_dict in todo_items]
    in_progress = [item_dict for _, item_dict in in_progress_items]
    
    # Sort completed by updated_at newest first
    completed_items.sort(key=lambda t: t.updated_at, reverse=True)
    completed = [ticket_to_dict(t) for t in completed_items]
    
    return {
        'todo': todo,
        'in_progress': in_progress,
        'completed': completed
    }


def filed(session, user: str) -> list:
    """Get all tickets filed by a user.
    
    Args:
        session: Database session
        user: The user who filed the tickets ('her' or 'him')
    
    Returns:
        List of ticket_to_dict dicts, ordered by created_at newest first.
    """
    from app.models import Ticket
    from sqlalchemy import select
    
    stmt = select(Ticket).where(Ticket.filed_by == user).order_by(Ticket.created_at.desc())
    tickets = session.execute(stmt).scalars().all()
    
    return [ticket_to_dict(t) for t in tickets]


def edit_ticket(session, ticket_id: int, user: str, data: dict) -> dict:
    """Edit a ticket.
    
    Args:
        session: Database session
        ticket_id: ID of the ticket to edit
        user: User attempting the edit (must be the filer)
        data: Dict with optional keys title, details, priority, due
              At least one key must be present
    
    Returns:
        ticket_to_dict of the updated ticket
    
    Raises:
        LookupError: If ticket does not exist or user is not a party
        ValueError: If data is not a dict, is empty, has invalid keys,
                   or any field validation fails
        PermissionError: If user is not the filer
        NotEditable: If status is not open or acknowledged
    """
    from app.models import Ticket
    from app.activity import record_event
    
    # Check 1: LookupError - ticket must exist and user must be a party
    ticket = session.get(Ticket, ticket_id)
    if ticket is None:
        raise LookupError(f"Ticket {ticket_id} not found")
    
    if user != ticket.filed_by and user != ticket.assigned_to:
        raise LookupError(f"User '{user}' is not a party to ticket {ticket_id}")
    
    # Check 2: ValueError - data must be a dict
    if not isinstance(data, dict):
        raise ValueError("data must be a dict")
    
    # Check 2: ValueError - data must not be empty
    if len(data) == 0:
        raise ValueError("data must not be empty")
    
    # Check 2: ValueError - data must only have valid keys
    invalid_keys = set(data.keys()) - ALLOWED_DATA_KEYS
    if invalid_keys:
        raise ValueError(f"data contains invalid keys: {invalid_keys}")
    
    # Validate field values (raises ValueError if invalid) - do this before other checks
    # to ensure we catch value errors before permission/status checks
    validated_values = {}
    if 'title' in data:
        validated_values['title'] = _validate_title(data['title'])
    if 'details' in data:
        validated_values['details'] = _validate_details(data['details'])
    if 'priority' in data:
        validated_values['priority'] = _validate_priority(data['priority'])
    if 'due' in data:
        validated_values['due'] = _validate_due(data['due'])
    
    # Check 3: PermissionError - user must be the filer
    if user != ticket.filed_by:
        raise PermissionError(f"User '{user}' is not the filer of ticket {ticket_id}")
    
    # Check 4: NotEditable - status must be open or acknowledged
    if ticket.status not in ('open', 'acknowledged'):
        raise NotEditable(f"Ticket {ticket_id} with status '{ticket.status}' is not editable")
    
    # All checks passed - perform the update
    now = datetime.now(timezone.utc)
    
    if 'title' in validated_values:
        ticket.title = validated_values['title']
    if 'details' in validated_values:
        ticket.details = validated_values['details']
    if 'priority' in validated_values:
        ticket.priority = validated_values['priority']
    if 'due' in validated_values:
        ticket.due = validated_values['due']
    
    ticket.updated_at = now
    
    # Record the 'edited' event (not committed yet)
    record_event(session, ticket, user, 'edited', from_status=None, to_status=None)
    
    session.commit()
    
    return ticket_to_dict(ticket)
