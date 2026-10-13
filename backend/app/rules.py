from datetime import datetime, timezone

from app.models import Ticket


def ticket_to_dict(ticket: Ticket) -> dict:
    """Convert a Ticket to a dictionary."""
    return {
        "id": ticket.id,
        "title": ticket.title,
        "details": ticket.details,
        "priority": ticket.priority,
        "due": ticket.due.strftime("%Y-%m-%d") if ticket.due else None,
        "status": ticket.status,
        "filed_by": ticket.filed_by,
        "assigned_to": ticket.assigned_to,
        "created_at": ticket.created_at.isoformat(),
        "updated_at": ticket.updated_at.isoformat(),
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
    ticket.status = new_status
    ticket.updated_at = datetime.now(timezone.utc)
    session.commit()
    
    return ticket_to_dict(ticket)
