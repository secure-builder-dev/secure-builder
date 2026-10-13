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
