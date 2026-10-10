from datetime import datetime, date, timedelta, timezone
from sqlalchemy import and_
from app.models import Ticket

USERS = ("her", "him")

def create_ticket(session, filed_by, data):
    if filed_by not in USERS:
        raise ValueError("Invalid user")

    title = data.get("title", "").strip()
    if not title or len(title) < 1 or len(title) > 120:
        raise ValueError("Invalid title")

    details = data.get("details", "")
    if len(details) > 1000:
        raise ValueError("Details too long")

    priority = data.get("priority", "normal")
    if priority not in ("low", "normal", "urgent"):
        raise ValueError("Invalid priority")

    due = data.get("due")
    if due is not None:
        try:
            due_date = datetime.strptime(due, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError("Invalid due date")
    else:
        due_date = None

    if set(data.keys()) - {"title", "details", "priority", "due"}:
        raise ValueError("Extra keys in data")

    assigned_to = "him" if filed_by == "her" else "her"

    ticket = Ticket(
        title=title,
        details=details,
        priority=priority,
        due=due_date,
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
        "due": ticket.due.strftime("%Y-%m-%d") if ticket.due else None,
        "status": ticket.status,
        "filed_by": ticket.filed_by,
        "assigned_to": ticket.assigned_to,
        "created_at": ticket.created_at.isoformat(),
        "updated_at": ticket.updated_at.isoformat()
    }

def change_status(session, ticket_id, user, new_status):
    ticket = session.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise LookupError("Ticket not found")

    if user not in (ticket.filed_by, ticket.assigned_to):
        raise LookupError("User is not a party to this ticket")

    if new_status not in ("open", "acknowledged", "in_progress", "done", "closed"):
        raise ValueError("Unknown status")

    allowed_moves = {
        ("open", "acknowledged"): "assigned_to",
        ("acknowledged", "in_progress"): "assigned_to",
        ("in_progress", "done"): "assigned_to",
        ("done", "closed"): "filed_by",
        ("done", "open"): "filed_by",
        ("closed", "open"): "filed_by"
    }

    # Determine the correct user based on the move
    if move in allowed_moves:
        required_user = allowed_moves[move]
        if required_user == "assigned_to":
            required_user = ticket.assigned_to
        elif required_user == "filed_by":
            required_user = ticket.filed_by
        
        if user != required_user:
            raise PermissionError("User cannot make this move")

    move = (ticket.status, new_status)
    if move not in allowed_moves:
        raise ValueError("Invalid status move")

    if allowed_moves[move] != user:
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
        "due": ticket.due.strftime("%Y-%m-%d") if ticket.due else None,
        "status": ticket.status,
        "filed_by": ticket.filed_by,
        "assigned_to": ticket.assigned_to,
        "created_at": ticket.created_at.isoformat(),
        "updated_at": ticket.updated_at.isoformat()
    }

def dashboard(session, user, today):
    tickets = session.query(Ticket).filter(Ticket.assigned_to == user).all()

    todo = []
    in_progress = []
    completed = []

    for ticket in tickets:
        if ticket.status in ("open", "acknowledged"):
            # Determine group based on due date
            if ticket.due is None:
                group = 2
            elif ticket.due < today:
                group = 0
            elif ticket.due <= today + timedelta(days=3):
                group = 1
            else:
                group = 2

            todo.append({
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
                "group": group
            })
        elif ticket.status == "in_progress":
            # Determine group based on due date
            if ticket.due is None:
                group = 2
            elif ticket.due < today:
                group = 0
            elif ticket.due <= today + timedelta(days=3):
                group = 1
            else:
                group = 2

            in_progress.append({
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
                    "due": ticket.due.strftime("%Y-%m-%d") if ticket.due else None,
                    "status": ticket.status,
                    "filed_by": ticket.filed_by,
                    "assigned_to": ticket.assigned_to,
                    "created_at": ticket.created_at.isoformat(),
                    "updated_at": ticket.updated_at.isoformat()
                })

    # Sort todo and in_progress by group, then due date (None last), then created_at
    todo.sort(key=lambda x: (x["group"], x["due"] if x["due"] else date.max, x["created_at"]))
    in_progress.sort(key=lambda x: (x["group"], x["due"] if x["due"] else date.max, x["created_at"]))
    completed.sort(key=lambda x: x["updated_at"], reverse=True)

    return {
        "todo": todo,
        "in_progress": in_progress,
        "completed": completed
    }

def filed(session, user):
    tickets = session.query(Ticket).filter(Ticket.filed_by == user).order_by(Ticket.created_at.desc()).all()

    return [{
        "id": ticket.id,
        "title": ticket.title,
        "details": ticket.details,
        "priority": ticket.priority,
        "due": ticket.due.strftime("%Y-%m-%d") if ticket.due else None,
        "status": ticket.status,
        "filed_by": ticket.filed_by,
        "assigned_to": ticket.assigned_to,
        "created_at": ticket.created_at.isoformat(),
        "updated_at": ticket.updated_at.isoformat()
    } for ticket in tickets]