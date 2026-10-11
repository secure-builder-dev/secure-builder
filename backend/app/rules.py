from datetime import datetime, date, timedelta, timezone
from sqlalchemy import and_
from sqlalchemy.orm import Session
from app.models import Ticket

USERS = ("her", "him")


def create_ticket(session: Session, filed_by: str, data: dict) -> dict:
    if filed_by not in USERS:
        raise ValueError("Invalid user")
    
    title = data.get("title", "").strip()
    if not title or len(title) > 120:
        raise ValueError("Invalid title")
    
    details = data.get("details", "")
    if len(details) > 1000:
        raise ValueError("Details too long")
    
    priority = data.get("priority", "normal")
    if priority not in ("low", "normal", "urgent"):
        raise ValueError("Invalid priority")
    
    due_str = data.get("due")
    due = None
    if due_str:
        try:
            due = datetime.strptime(due_str, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError("Invalid due date")
    
    if set(data.keys()) - {"title", "details", "priority", "due"}:
        raise ValueError("Extra keys in data")
    
    assigned_to = "him" if filed_by == "her" else "her"
    
    ticket = Ticket(
        title=title,
        details=details,
        priority=priority,
        due=due,
        status="open",
        filed_by=filed_by,
        assigned_to=assigned_to,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    session.add(ticket)
    session.commit()
    session.refresh(ticket)
    
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
        "updated_at": ticket.updated_at.isoformat()
    }


def change_status(session: Session, ticket_id: int, user: str, new_status: str) -> dict:
    ticket = session.get(Ticket, ticket_id)
    if not ticket:
        raise LookupError("Ticket not found")
    
    if user not in (ticket.filed_by, ticket.assigned_to):
        raise LookupError("User is not a party to this ticket")
    
    status_moves = {
        ("open", "acknowledged"): "him",
        ("acknowledged", "in_progress"): "him",
        ("in_progress", "done"): "him",
        ("done", "closed"): "her",
        ("done", "open"): "her",
        ("closed", "open"): "her",
    }
    
    key = (ticket.status, new_status)
    if key not in status_moves:
        raise ValueError("Invalid status move")
    
    if status_moves[key] != user:
        raise PermissionError("User cannot make this move")
    
    ticket.status = new_status
    ticket.updated_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(ticket)
    
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
        "updated_at": ticket.updated_at.isoformat()
    }


def dashboard(session: Session, user: str, today: date) -> dict:
    todo = []
    in_progress = []
    completed = []
    
    # Get tickets assigned to user
    tickets = session.query(Ticket).filter(Ticket.assigned_to == user).all()
    
    for ticket in tickets:
        if ticket.status in ("open", "acknowledged"):
            group = 0
            if ticket.priority == "urgent":
                group = 0
            elif ticket.due and ticket.due < today:
                group = 0
            elif ticket.due and ticket.due <= today + timedelta(days=3):
                group = 1
            else:
                group = 2
            
            todo.append({
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
                "group": group
            })
        elif ticket.status == "in_progress":
            group = 0
            if ticket.priority == "urgent":
                group = 0
            elif ticket.due and ticket.due < today:
                group = 0
            elif ticket.due and ticket.due <= today + timedelta(days=3):
                group = 1
            else:
                group = 2
            
            in_progress.append({
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
                "group": group
            })
        elif ticket.status in ("done", "closed"):
            updated_date = ticket.updated_at.date()
            if today - timedelta(days=7) <= updated_date <= today:
                completed.append({
                    "id": ticket.id,
                    "title": ticket.title,
                    "details": ticket.details,
                    "priority": ticket.priority,
                    "due": ticket.due.isoformat() if ticket.due else None,
                    "status": ticket.status,
                    "filed_by": ticket.filed_by,
                    "assigned_to": ticket.assigned_to,
                    "created_at": ticket.created_at.isoformat(),
                    "updated_at": ticket.updated_at.isoformat()
                })
    
    # Sort todo and in_progress
    todo.sort(key=lambda x: (x["group"], x["due"] if x["due"] else date.max, x["created_at"]))
    in_progress.sort(key=lambda x: (x["group"], x["due"] if x["due"] else date.max, x["created_at"]))
    
    # Sort completed by updated_at descending
    completed.sort(key=lambda x: x["updated_at"], reverse=True)
    
    return {
        "todo": todo,
        "in_progress": in_progress,
        "completed": completed
    }


def filed(session: Session, user: str) -> list:
    tickets = session.query(Ticket).filter(Ticket.filed_by == user).order_by(Ticket.created_at.desc()).all()
    
    return [{
        "id": ticket.id,
        "title": ticket.title,
        "details": ticket.details,
        "priority": ticket.priority,
        "due": ticket.due.isoformat() if ticket.due else None,
        "status": ticket.status,
        "filed_by": ticket.filed_by,
        "assigned_to": ticket.assigned_to,
        "created_at": ticket.created_at.isoformat(),
        "updated_at": ticket.updated_at.isoformat()
    } for ticket in tickets]