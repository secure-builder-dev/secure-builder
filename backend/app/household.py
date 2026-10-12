"""GD-2c: household_board — every ticket of both users."""
import datetime as dt
from typing import Any

from sqlalchemy import select

from app.db import Base
from app.models import Ticket
from app.rules import ticket_to_dict


def household_board(session, today: dt.date) -> dict[str, list[dict[str, Any]]]:
    """Return the household board with every ticket of both users."""
    # Get all tickets for both users
    tickets = session.query(Ticket).all()

    todo = []
    in_progress = []
    completed = []

    for ticket in tickets:
        t_dict = ticket_to_dict(ticket)
        
        # Determine which column the ticket belongs to
        if ticket.status in ("open", "acknowledged"):
            todo.append(t_dict)
        elif ticket.status == "in_progress":
            in_progress.append(t_dict)
        elif ticket.status in ("done", "closed"):
            # Check if updated_at is within the 7 days ending today
            updated_date = ticket.updated_at.date()
            if updated_date >= today - dt.timedelta(days=6) and updated_date <= today:
                completed.append(t_dict)

    # Sort todo and in_progress by created_at oldest first
    todo.sort(key=lambda t: dt.datetime.fromisoformat(t["created_at"]))
    in_progress.sort(key=lambda t: dt.datetime.fromisoformat(t["created_at"]))

    # Sort completed by updated_at newest first
    completed.sort(key=lambda t: dt.datetime.fromisoformat(t["updated_at"]), reverse=True)

    return {
        "todo": todo,
        "in_progress": in_progress,
        "completed": completed,
    }
