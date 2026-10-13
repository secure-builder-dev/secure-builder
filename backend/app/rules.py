from datetime import date, datetime, timezone
from typing import Optional
import time

from app.models import Ticket


def ticket_to_dict(ticket: Ticket) -> dict:
    """Convert a Ticket to a dictionary."""
    due_str = None
    if ticket.due is not None:
        if isinstance(ticket.due, datetime):
            due_str = ticket.due.strftime("%Y-%m-%d")
        elif isinstance(ticket.due, date):
            due_str = ticket.due.isoformat()
        else:
            due_str = str(ticket.due)
    
    # Ensure timestamps are timezone-aware UTC before converting
    created_at = ticket.created_at
    updated_at = ticket.updated_at
    
    if not created_at.tzinfo:
        created_at = created_at.replace(tzinfo=timezone.utc)
    if not updated_at.tzinfo:
        updated_at = updated_at.replace(tzinfo=timezone.utc)
    
    return {
        "id": ticket.id,
        "title": ticket.title,
        "details": ticket.details,
        "priority": ticket.priority,
        "due": due_str,
        "status": ticket.status,
        "filed_by": ticket.filed_by,
        "assigned_to": ticket.assigned_to,
        "created_at": created_at.isoformat().replace("+00:00", "Z"),
        "updated_at": updated_at.isoformat().replace("+00:00", "Z"),
    }


# Status transition table: (from_status, to_status) -> required_role
# role is either "filer" or "assignee"
STATUS_TRANSITIONS = {
    ("open", "acknowledged"): "assignee",
    ("acknowledged", "in_progress"): "assignee",
    ("in_progress", "done"): "assignee",
    ("done", "closed"): "filer",
    ("done", "open"): "filer",
    ("closed", "open"): "filer",
}

VALID_STATUSES = {"open", "acknowledged", "in_progress", "done", "closed"}


def change_status(session, ticket_id: int, user: str, new_status: str) -> dict:
    """
    Change the status of a ticket according to the design's status table.
    
    Raises:
        LookupError: if ticket does not exist or user is neither filer nor assignee
        ValueError: if new_status is invalid or the move is not in the table
        PermissionError: if the move is valid but user is not the required party
    """
    # Check if ticket exists and user is a party (LookupError check first)
    ticket = session.get(Ticket, ticket_id)
    if ticket is None:
        raise LookupError(f"Ticket {ticket_id} not found")
    
    if user != ticket.filed_by and user != ticket.assigned_to:
        raise LookupError(f"User '{user}' is not a party to ticket {ticket_id}")
    
    # Check if new_status is valid (ValueError check)
    if new_status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {new_status}")
    
    current_status = ticket.status
    
    # Check if the move is in the table (ValueError check)
    transition_key = (current_status, new_status)
    if transition_key not in STATUS_TRANSITIONS:
        raise ValueError(f"Invalid transition from {current_status} to {new_status}")
    
    # Check if user has permission for this transition (PermissionError check)
    required_role = STATUS_TRANSITIONS[transition_key]
    if required_role == "filer" and user != ticket.filed_by:
        raise PermissionError(f"User '{user}' is not the filer")
    if required_role == "assignee" and user != ticket.assigned_to:
        raise PermissionError(f"User '{user}' is not the assignee")
    
    # Perform the status change
    now = datetime.now(timezone.utc)
    ticket.status = new_status
    ticket.updated_at = now
    session.commit()
    
    return ticket_to_dict(ticket)


def create_ticket(
    session,
    title: str,
    details: str,
    priority: str,
    due: Optional[date],
    user: str
) -> dict:
    """
    Create a new ticket.
    
    Args:
        session: Database session
        title: Ticket title (1-120 chars after stripping)
        details: Ticket details (0-1000 chars, default "")
        priority: Priority level (low | normal | urgent, default "normal")
        due: Due date or None
        user: The user filing the ticket
    
    Returns:
        Dictionary representation of the created ticket
    
    Raises:
        ValueError: If title is invalid, details too long, priority invalid, or due invalid
    """
    # Validate title
    stripped_title = title.strip()
    if not stripped_title or len(stripped_title) > 120:
        raise ValueError("Title must be 1-120 characters")
    
    # Validate details
    if not isinstance(details, str):
        raise ValueError("Details must be a string")
    if len(details) > 1000:
        raise ValueError("Details must be 0-1000 characters")
    
    # Validate priority
    valid_priorities = {"low", "normal", "urgent"}
    if priority not in valid_priorities:
        raise ValueError(f"Invalid priority: {priority}")
    
    # Create ticket
    now = datetime.now(timezone.utc)
    ticket = Ticket(
        title=stripped_title,
        details=details if details else "",
        priority=priority,
        due=due,
        status="open",
        filed_by=user,
        assigned_to="him" if user == "her" else "her",
        created_at=now,
        updated_at=now
    )
    
    session.add(ticket)
    session.commit()
    
    return ticket_to_dict(ticket)


def _compute_group(priority: str, due: Optional[date], today: date) -> int:
    """
    Compute the group value for a ticket.
    
    Group 0: urgent priority OR due before today
    Group 1: due today or within 3 days after today
    Group 2: otherwise (due more than 3 days away, or no due date)
    """
    # Group 0: urgent or overdue
    if priority == "urgent":
        return 0
    if due is not None and due < today:
        return 0
    
    # Group 1: due today or within next 3 days
    if due is not None:
        days_until_due = (due - today).days
        if 0 <= days_until_due <= 3:
            return 1
    
    # Group 2: everything else
    return 2


def _sort_key_for_active(ticket: Ticket, today: date):
    """
    Sort key for todo and in_progress tickets.
    Order by: group (0, 1, 2), then due date (none last), then created_at oldest first.
    """
    group = _compute_group(ticket.priority, ticket.due, today)
    
    # For due date sorting: None should come last
    # We use a tuple: (has_due, due_date) where has_due is 0 for dates, 1 for None
    if ticket.due is not None:
        due_sort = (0, ticket.due)
    else:
        due_sort = (1, date.max)
    
    return (group, due_sort, ticket.created_at)


def dashboard(session, user: str, today: date) -> dict:
    """
    Get the personal board for a user.
    
    Returns:
        Dict with 'todo', 'in_progress', 'completed' lists of ticket dicts.
        todo and in_progress include a 'group' key.
        completed does not include a 'group' key.
    """
    # Get all tickets assigned to this user
    all_tickets = session.query(Ticket).filter(
        Ticket.assigned_to == user
    ).all()
    
    todo = []
    in_progress = []
    completed = []
    
    # Calculate the 7-day window for completed (today + 6 days before)
    window_start = today - timedelta(days=6)
    
    for ticket in all_tickets:
        if ticket.status in ("open", "acknowledged"):
            # Todo tickets
            t_dict = ticket_to_dict(ticket)
            t_dict["group"] = _compute_group(ticket.priority, ticket.due, today)
            todo.append(t_dict)
        elif ticket.status == "in_progress":
            # In progress tickets
            t_dict = ticket_to_dict(ticket)
            t_dict["group"] = _compute_group(ticket.priority, ticket.due, today)
            in_progress.append(t_dict)
        elif ticket.status in ("done", "closed"):
            # Check if within the 7-day window based on updated_at date
            updated_date = ticket.updated_at.date() if ticket.updated_at.tzinfo else ticket.updated_at.replace(tzinfo=timezone.utc).date()
            if window_start <= updated_date <= today:
                completed.append(ticket_to_dict(ticket))
    
    # Sort todo and in_progress by group, then due date (none last), then created_at
    todo.sort(key=lambda t: _sort_key_for_active_by_dict(t, today))
    in_progress.sort(key=lambda t: _sort_key_for_active_by_dict(t, today))
    
    # Sort completed by updated_at newest first
    completed.sort(key=lambda t: t["updated_at"], reverse=True)
    
    return {
        "todo": todo,
        "in_progress": in_progress,
        "completed": completed
    }


def _sort_key_for_active_by_dict(ticket_dict: dict, today: date):
    """
    Sort key for ticket dicts in todo and in_progress.
    Order by: group, then due date (none last), then created_at oldest first.
    """
    group = ticket_dict["group"]
    priority = ticket_dict["priority"]
    due_str = ticket_dict["due"]
    
    # Parse due date
    if due_str is not None:
        due = date.fromisoformat(due_str)
        due_sort = (0, due)
    else:
        due_sort = (1, date.max)
    
    # Parse created_at for sorting
    created_at = datetime.fromisoformat(ticket_dict["created_at"].replace("Z", "+00:00"))
    
    return (group, due_sort, created_at)


def filed(session, user: str) -> list:
    """
    Get all tickets filed by a user, ordered by newest created_at first.
    
    Returns:
        List of ticket dicts.
    """
    tickets = session.query(Ticket).filter(
        Ticket.filed_by == user
    ).order_by(Ticket.created_at.desc()).all()
    
    return [ticket_to_dict(t) for t in tickets]


from datetime import timedelta


class NotEditable(Exception):
    """Raised when a ticket cannot be edited (status is not open or acknowledged)."""
    pass


def edit_ticket(session, ticket_id: int, user: str, data: dict) -> dict:
    """
    Edit a ticket's fields.
    
    Args:
        session: Database session
        ticket_id: ID of the ticket to edit
        user: User attempting the edit (must be the filer)
        data: Dict with fields to update (title, details, priority, due)
    
    Returns:
        Dictionary representation of the updated ticket
    
    Raises:
        LookupError: if ticket does not exist or user is not a party
        ValueError: if data is invalid
        PermissionError: if user is not the filer
        NotEditable: if status is not open or acknowledged
    """
    # Check if ticket exists and user is a party
    ticket = session.get(Ticket, ticket_id)
    if ticket is None:
        raise LookupError(f"Ticket {ticket_id} not found")
    
    if user != ticket.filed_by and user != ticket.assigned_to:
        raise LookupError(f"User '{user}' is not a party to ticket {ticket_id}")
    
    # Validate data
    if not isinstance(data, dict):
        raise ValueError("Data must be a dictionary")
    
    if not data:
        raise ValueError("Data cannot be empty")
    
    valid_keys = {"title", "details", "priority", "due"}
    for key in data.keys():
        if key not in valid_keys:
            raise ValueError(f"Invalid key: {key}")
    
    # Validate each field value
    if "title" in data:
        stripped_title = data["title"].strip()
        if not stripped_title or len(stripped_title) > 120:
            raise ValueError("Title must be 1-120 characters")
    
    if "details" in data:
        if not isinstance(data["details"], str):
            raise ValueError("Details must be a string")
        if len(data["details"]) > 1000:
            raise ValueError("Details must be 0-1000 characters")
    
    if "priority" in data:
        valid_priorities = {"low", "normal", "urgent"}
        if data["priority"] not in valid_priorities:
            raise ValueError(f"Invalid priority: {data['priority']}")
    
    if "due" in data:
        due_val = data["due"]
        if due_val is not None and not isinstance(due_val, date):
            raise ValueError("Due must be a date or None")
    
    # Check permission: only filer can edit
    if user != ticket.filed_by:
        raise PermissionError(f"User '{user}' is not the filer")
    
    # Check if editable (status must be open or acknowledged)
    if ticket.status not in ("open", "acknowledged"):
        raise NotEditable("Ticket is not editable in current status")
    
    # Apply changes
    if "title" in data:
        ticket.title = data["title"].strip()
    if "details" in data:
        ticket.details = data["details"] if data["details"] else ""
    if "priority" in data:
        ticket.priority = data["priority"]
    if "due" in data:
        ticket.due = data["due"]
    
    # Update timestamp
    ticket.updated_at = datetime.now(timezone.utc)
    session.commit()
    
    return ticket_to_dict(ticket)


def record_event(session, ticket: Ticket, actor: str, kind: str, from_status: Optional[str] = None, to_status: Optional[str] = None):
    """
    Record a ticket event.
    
    Note: This function is a placeholder. The actual implementation requires
    the TicketEvent model which is part of E3.
    """
    pass


def add_comment(session, ticket_id: int, user: str, body: str) -> dict:
    """
    Add a comment to a ticket.
    
    Note: This function is a placeholder. The actual implementation requires
    the Comment model which is part of E3.
    """
    pass


def list_comments(session, ticket_id: int, user: str) -> list:
    """
    List comments for a ticket.
    
    Note: This function is a placeholder. The actual implementation requires
    the Comment model which is part of E3.
    """
    pass


def ticket_history(session, ticket_id: int, user: str) -> list:
    """
    Get ticket history events.
    
    Note: This function is a placeholder. The actual implementation requires
    the TicketEvent model which is part of E3.
    """
    pass
