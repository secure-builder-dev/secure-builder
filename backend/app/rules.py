from datetime import datetime, date, timedelta, timezone
from typing import Any
from app.db import SessionLocal
from app.models import Ticket

USERS = ("her", "him")

VALID_PRIORITIES = {"low", "normal", "urgent"}
VALID_STATUSES = {"open", "acknowledged", "in_progress", "done", "closed"}

# Status transition table: (from_status, to_status) -> allowed_party ('filer' or 'assignee')
STATUS_TRANSITIONS = {
    ("open", "acknowledged"): "assignee",
    ("acknowledged", "in_progress"): "assignee",
    ("in_progress", "done"): "assignee",
    ("done", "closed"): "filer",
    ("done", "open"): "filer",
    ("closed", "open"): "filer",
}

def _ticket_to_dict(ticket: Ticket) -> dict[str, Any]:
    """Convert a Ticket model instance to a plain dict."""
    return {
        "id": ticket.id,
        "title": ticket.title,
        "details": ticket.details,
        "priority": str(ticket.priority),
        "due": ticket.due.isoformat() if ticket.due else None,
        "status": str(ticket.status),
        "filed_by": ticket.filed_by,
        "assigned_to": ticket.assigned_to,
        "created_at": ticket.created_at.isoformat(),
        "updated_at": ticket.updated_at.isoformat(),
    }

def create_ticket(session: SessionLocal, filed_by: str, data: dict[str, Any]) -> dict[str, Any]:
    """Create a new ticket."""
    # Validate filed_by
    if filed_by not in USERS:
        raise ValueError(f"filed_by must be one of {USERS}")
    
    # Validate allowed keys
    allowed_keys = {"title", "details", "priority", "due"}
    if not set(data.keys()).issubset(allowed_keys):
        raise ValueError("data contains invalid keys")
    
    # Extract and validate title
    title = data.get("title")
    if title is None:
        raise ValueError("title is required")
    title = str(title).strip()
    if not (1 <= len(title) <= 120):
        raise ValueError("title must be 1-120 characters after stripping")
    
    # Extract and validate details
    details = data.get("details", "")
    if details is None:
        details = ""
    details = str(details)
    if len(details) > 1000:
        raise ValueError("details must be at most 1000 characters")
    
    # Extract and validate priority
    priority = data.get("priority", "normal")
    if priority not in VALID_PRIORITIES:
        raise ValueError(f"priority must be one of {VALID_PRIORITIES}")
    
    # Extract and validate due date
    due_str = data.get("due")
    due: date | None = None
    if due_str is not None:
        try:
            due = date.fromisoformat(str(due_str))
        except (ValueError, TypeError):
            raise ValueError("due must be a valid YYYY-MM-DD date")
    
    # Determine assigned_to (the other user)
    assigned_to = "him" if filed_by == "her" else "her"
    
    # Create the ticket
    now = datetime.now(timezone.utc)
    ticket = Ticket(
        title=title,
        details=details,
        priority=priority,
        due=due,
        status="open",
        filed_by=filed_by,
        assigned_to=assigned_to,
        created_at=now,
        updated_at=now,
    )
    
    session.add(ticket)
    session.commit()
    
    return _ticket_to_dict(ticket)

def change_status(session: SessionLocal, ticket_id: int, user: str, new_status: str) -> dict[str, Any]:
    """Change the status of a ticket."""
    # Get the ticket
    ticket = session.get(Ticket, ticket_id)
    if ticket is None:
        raise LookupError(f"Ticket {ticket_id} not found")
    
    # Check if user is a party
    if user != ticket.filed_by and user != ticket.assigned_to:
        raise LookupError(f"User '{user}' is not a party to ticket {ticket_id}")
    
    # Validate new_status
    if new_status not in VALID_STATUSES:
        raise ValueError(f"Unknown status: {new_status}")
    
    current_status = ticket.status
    
    # Check if the transition is valid
    transition_key = (current_status, new_status)
    if transition_key not in STATUS_TRANSITIONS:
        raise ValueError(f"Invalid status transition from '{current_status}' to '{new_status}'")
    
    allowed_party = STATUS_TRANSITIONS[transition_key]
    
    # Check if user is the allowed party
    if allowed_party == "filer" and user != ticket.filed_by:
        raise PermissionError(f"Only the filer can perform this transition")
    if allowed_party == "assignee" and user != ticket.assigned_to:
        raise PermissionError(f"Only the assignee can perform this transition")
    
    # Apply the change
    ticket.status = new_status
    ticket.updated_at = datetime.now(timezone.utc)
    session.commit()
    
    return _ticket_to_dict(ticket)

def _calculate_group(priority: str, due: date | None, today: date) -> int:
    """Calculate the group for sorting."""
    # Group 0: urgent or overdue (due before today)
    if priority == "urgent" or (due is not None and due < today):
        return 0
    # Group 1: due today or within 3 days after today
    if due is not None and today <= due <= today + timedelta(days=3):
        return 1
    # Group 2: everything else
    return 2

def dashboard(session: SessionLocal, user: str, today: date) -> dict[str, list[dict[str, Any]]]:
    """Get the dashboard for a user."""
    from sqlalchemy import select
    
    # Get tickets assigned to user with status open or acknowledged (todo)
    todo_query = (
        select(Ticket)
        .where(Ticket.assigned_to == user)
        .where(Ticket.status.in_(("open", "acknowledged")))
    )
    todo_tickets = session.execute(todo_query).scalars().all()
    
    # Get tickets assigned to user with status in_progress
    in_progress_query = (
        select(Ticket)
        .where(Ticket.assigned_to == user)
        .where(Ticket.status == "in_progress")
    )
    in_progress_tickets = session.execute(in_progress_query).scalars().all()
    
    # Get completed tickets (done or closed) within 7 days ending today
    seven_days_ago = today - timedelta(days=7)
    completed_query = (
        select(Ticket)
        .where(Ticket.assigned_to == user)
        .where(Ticket.status.in_(("done", "closed")))
        .where(Ticket.updated_at >= datetime.combine(seven_days_ago, datetime.min.time(), tzinfo=timezone.utc))
        .where(Ticket.updated_at < datetime.combine(today + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc))
    )
    completed_tickets = session.execute(completed_query).scalars().all()
    
    # Process todo tickets
    todo_list = []
    for t in todo_tickets:
        ticket_dict = _ticket_to_dict(t)
        ticket_dict["group"] = _calculate_group(t.priority, t.due, today)
        todo_list.append(ticket_dict)
    
    # Sort todo: group, then due (None last), then created_at
    def sort_key(todo_item):
        group = todo_item["group"]
        due_val = todo_item["due"]
        # For sorting: None should be last, so use a tuple (0, max_date) for None, (1, date) for actual dates
        if due_val is None:
            due_sort = (1, date.max)
        else:
            due_sort = (0, date.fromisoformat(due_val))
        created_at = datetime.fromisoformat(todo_item["created_at"])
        return (group, due_sort, created_at)
    
    todo_list.sort(key=sort_key)
    
    # Process in_progress tickets
    in_progress_list = []
    for t in in_progress_tickets:
        ticket_dict = _ticket_to_dict(t)
        ticket_dict["group"] = _calculate_group(t.priority, t.due, today)
        in_progress_list.append(ticket_dict)
    
    # Sort in_progress: same as todo
    in_progress_list.sort(key=sort_key)
    
    # Process completed tickets (newest updated_at first)
    completed_list = []
    for t in completed_tickets:
        ticket_dict = _ticket_to_dict(t)
        completed_list.append(ticket_dict)
    
    # Sort completed: newest updated_at first
    completed_list.sort(key=lambda x: datetime.fromisoformat(x["updated_at"]), reverse=True)
    
    return {
        "todo": todo_list,
        "in_progress": in_progress_list,
        "completed": completed_list,
    }

def filed(session: SessionLocal, user: str) -> list[dict[str, Any]]:
    """Get tickets filed by a user."""
    from sqlalchemy import select
    
    query = (
        select(Ticket)
        .where(Ticket.filed_by == user)
        .order_by(Ticket.created_at.desc())
    )
    tickets = session.execute(query).scalars().all()
    
    return [_ticket_to_dict(t) for t in tickets]