from datetime import datetime, date, timedelta, timezone
from sqlalchemy.orm import Session
from app.models import Ticket

USERS = ("her", "him")

ALLOWED_MOVES = {
    ("open", "acknowledged"): "assigned_to",
    ("acknowledged", "in_progress"): "assigned_to",
    ("in_progress", "done"): "assigned_to",
    ("done", "closed"): "filed_by",
    ("done", "open"): "filed_by",
    ("closed", "open"): "filed_by",
}

def create_ticket(session: Session, filed_by: str, data: dict) -> dict:
    if filed_by not in USERS:
        raise ValueError("filed_by must be one of the allowed users")

    title = data.get("title", "").strip()
    if not title or len(title) > 120:
        raise ValueError("title must be 1-120 characters")

    details = data.get("details", "")
    if len(details) > 1000:
        raise ValueError("details must be at most 1000 characters")

    priority = data.get("priority", "normal")
    if priority not in ("low", "normal", "urgent"):
        raise ValueError("priority must be 'low', 'normal', or 'urgent'")

    due_str = data.get("due")
    due = None
    if due_str:
        try:
            due = datetime.strptime(due_str, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError("due must be a valid YYYY-MM-DD date")

    if set(data.keys()) - {"title", "details", "priority", "due"}:
        raise ValueError("data contains invalid keys")

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
        updated_at=datetime.now(timezone.utc),
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
        "updated_at": ticket.updated_at.isoformat(),
    }

def change_status(session: Session, ticket_id: int, user: str, new_status: str) -> dict:
    ticket = session.get(Ticket, ticket_id)
    if not ticket:
        raise LookupError("ticket not found")

    if user not in (ticket.filed_by, ticket.assigned_to):
        raise LookupError("user is not a party to this ticket")

    from_status = ticket.status
    if (from_status, new_status) not in ALLOWED_MOVES:
        raise ValueError("invalid move")

    allowed_user = ALLOWED_MOVES[(from_status, new_status)]
    if user != allowed_user:
        raise PermissionError("user is not allowed to make this move")

    allowed_user = ALLOWED_MOVES[(from_status, new_status)]
    if user != allowed_user:
        raise PermissionError("user is not allowed to make this move")

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
        "updated_at": ticket.updated_at.isoformat(),
    }

def dashboard(session: Session, user: str, today: date) -> dict:
    todo = []
    in_progress = []
    completed = []

    tickets = session.query(Ticket).filter(Ticket.assigned_to == user).all()

    for ticket in tickets:
        if ticket.status in ("open", "acknowledged"):
            if ticket.priority == "urgent" or (ticket.due and ticket.due < today):
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
                "group": group,
            })
        elif ticket.status == "in_progress":
            if ticket.priority == "urgent" or (ticket.due and ticket.due < today):
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
                "group": group,
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
                    "updated_at": ticket.updated_at.isoformat(),
                })

    todo.sort(key=lambda x: (x["group"], x["due"] or date.max, x["created_at"]))
    in_progress.sort(key=lambda x: (x["group"], x["due"] or date.max, x["created_at"]))
    completed.sort(key=lambda x: x["updated_at"], reverse=True)

    return {
        "todo": todo,
        "in_progress": in_progress,
        "completed": completed,
    }

def filed(session: Session, user: str) -> list[dict]:
    tickets = session.query(Ticket).filter(Ticket.filed_by == user).order_by(Ticket.created_at.desc()).all()

    return [
        {
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
        for ticket in tickets
    ]