import datetime as dt
from typing import Optional

from app.models import Ticket
from sqlalchemy.orm import Session


def create_ticket(
    session: Session,
    caller: str,
    data: dict,
) -> Ticket:
    """Create a new ticket.
    
    Args:
        session: Database session
        caller: 'her' or 'him'
        data: Dict with title, details, priority, due keys
        
    Returns:
        The created Ticket instance
        
    Raises:
        ValueError: If validation fails
    """
    title = data.get("title", "")
    details = data.get("details", "")
    priority = data.get("priority", "normal")
    due = data.get("due")
    
    # Validate title
    if not title or len(title.strip()) > 120:
        raise ValueError("invalid request")
    
    # Validate details
    if details and len(details) > 1000:
        raise ValueError("invalid request")
    
    # Validate priority
    if priority not in ("low", "normal", "urgent"):
        raise ValueError("invalid request")
    
    # Validate due date
    due_date: Optional[dt.date] = None
    if due is not None:
        try:
            due_date = dt.datetime.strptime(due, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError("invalid request")
    
    # Determine assigned_to (the other user)
    assigned_to = "her" if caller == "him" else "him"
    
    now = dt.datetime.now(dt.timezone.utc)
    ticket = Ticket(
        title=title.strip(),
        details=details or "",
        priority=priority,
        due=due_date,
        status="open",
        filed_by=caller,
        assigned_to=assigned_to,
        created_at=now,
        updated_at=now,
    )
    session.add(ticket)
    session.commit()
    return ticket


def change_status(
    session: Session,
    ticket_id: int,
    new_status: str,
    caller: str,
) -> Ticket:
    """Change the status of a ticket.
    
    Args:
        session: Database session
        ticket_id: The ticket ID
        new_status: The new status value
        caller: 'her' or 'him'
        
    Returns:
        The updated Ticket instance
        
    Raises:
        LookupError: If ticket not found or caller is not a party
        ValueError: If status transition is invalid
        PermissionError: If caller doesn't have permission for this transition
    """
    ticket = session.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise LookupError("not found")
    
    # Check if caller is a party
    if caller != ticket.filed_by and caller != ticket.assigned_to:
        raise LookupError("not found")
    
    current_status = ticket.status
    
    # Define valid transitions: (from, to) -> required_party
    transitions = {
        ("open", "acknowledged"): "assignee",
        ("acknowledged", "in_progress"): "assignee",
        ("in_progress", "done"): "assignee",
        ("done", "closed"): "filer",
        ("done", "open"): "filer",
        ("closed", "open"): "filer",
    }
    
    if (current_status, new_status) not in transitions:
        raise ValueError("invalid transition")
    
    required_party = transitions[(current_status, new_status)]
    if required_party == "assignee" and caller != ticket.assigned_to:
        raise PermissionError("forbidden")
    if required_party == "filer" and caller != ticket.filed_by:
        raise PermissionError("forbidden")
    
    ticket.status = new_status
    ticket.updated_at = dt.datetime.now(dt.timezone.utc)
    session.commit()
    return ticket


def ticket_to_dict(ticket: Ticket) -> dict:
    """Convert a Ticket model to a dict."""
    return {
        "id": ticket.id,
        "title": ticket.title,
        "details": ticket.details,
        "priority": ticket.priority,
        "due": ticket.due.isoformat() if ticket.due else None,
        "status": ticket.status,
        "filed_by": ticket.filed_by,
        "assigned_to": ticket.assigned_to,
        "created_at": ticket.created_at.isoformat(),
        "updated_at": ticket.updated_at.isoformat(),
    }


def dashboard(session: Session, caller: str, today: dt.date) -> dict:
    """Get the personal board for a user.
    
    Args:
        session: Database session
        caller: 'her' or 'him'
        today: Current UTC date
        
    Returns:
        Dict with todo, in_progress, completed lists
    """
    from datetime import timedelta
    
    # Tickets assigned to caller
    assigned = session.query(Ticket).filter(Ticket.assigned_to == caller).all()
    
    todo = []
    in_progress = []
    completed = []
    
    seven_days_ago = today - timedelta(days=7)
    
    for t in assigned:
        ticket_dict = ticket_to_dict(t)
        
        if t.status in ("open", "acknowledged"):
            due_before = t.due is not None and t.due < today
            due_today_or_3days = (
                t.due is not None and 
                t.due >= today and 
                t.due <= today + timedelta(days=3)
            )
            if t.priority == "urgent" or due_before:
                ticket_dict["group"] = 0
            elif due_today_or_3days:
                ticket_dict["group"] = 1
            else:
                ticket_dict["group"] = 2
            todo.append(ticket_dict)
        elif t.status == "in_progress":
            due_before = t.due is not None and t.due < today
            due_today_or_3days = (
                t.due is not None and 
                t.due >= today and 
                t.due <= today + timedelta(days=3)
            )
            if t.priority == "urgent" or due_before:
                ticket_dict["group"] = 0
            elif due_today_or_3days:
                ticket_dict["group"] = 1
            else:
                ticket_dict["group"] = 2
            in_progress.append(ticket_dict)
        elif t.status in ("done", "closed"):
            update_date = t.updated_at.date()
            if update_date >= seven_days_ago and update_date <= today:
                completed.append(ticket_dict)
    
    def sort_key(t):
        g = t.get("group", 2)
        due = t["due"]
        if due is None:
            due_sort = "9999-12-31"
        else:
            due_sort = due
        return (g, due_sort, t["created_at"])
    
    todo.sort(key=sort_key)
    in_progress.sort(key=sort_key)
    completed.sort(key=lambda t: t["updated_at"], reverse=True)
    
    return {"todo": todo, "in_progress": in_progress, "completed": completed}


def filed_tickets(session: Session, caller: str) -> list:
    """Get tickets filed by a user.
    
    Args:
        session: Database session
        caller: 'her' or 'him'
        
    Returns:
        List of ticket dicts, ordered by created_at descending
    """
    tickets = session.query(Ticket).filter(
        Ticket.filed_by == caller
    ).order_by(Ticket.created_at.desc()).all()
    
    return [ticket_to_dict(t) for t in tickets]
