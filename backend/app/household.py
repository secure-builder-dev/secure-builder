from datetime import date, timedelta
from app.models import Ticket
from app.rules import ticket_to_dict
from sqlalchemy import select, or_, and_


def household_board(session, today: date, q=None, priority=None, assigned_to=None) -> dict:
    """Get the household board with all tickets from both users.
    
    Args:
        session: Database session
        today: The reference date for the completed window
        q: Optional search query (case-insensitive, matches title or details)
        priority: Optional priority filter ('low', 'normal', 'urgent')
        assigned_to: Optional assignee filter ('her' or 'him')
    
    Returns:
        Dict with keys 'todo', 'in_progress', 'completed', each a list of
        ticket_to_dict dicts (no 'group' key).
    """
    # Build the query with filters
    stmt = select(Ticket)
    
    # Apply q filter (case-insensitive search in title or details)
    if q is not None and q != "":
        q_lower = q.lower()
        stmt = stmt.where(
            or_(
                Ticket.title.ilike(f"%{q_lower}%"),
                Ticket.details.ilike(f"%{q_lower}%")
            )
        )
    
    # Apply priority filter (exact match)
    if priority is not None and priority != "":
        stmt = stmt.where(Ticket.priority == priority)
    
    # Apply assigned_to filter (exact match)
    if assigned_to is not None and assigned_to != "":
        stmt = stmt.where(Ticket.assigned_to == assigned_to)
    
    tickets = session.execute(stmt).scalars().all()
    
    todo_items = []
    in_progress_items = []
    completed_items = []
    
    # Calculate the 7-day window for completed (today + 6 days before)
    window_start = today - timedelta(days=6)
    
    for ticket in tickets:
        if ticket.status in ('open', 'acknowledged'):
            # Todo column
            ticket_dict = ticket_to_dict(ticket)
            todo_items.append(ticket_dict)
        elif ticket.status == 'in_progress':
            # In progress column
            ticket_dict = ticket_to_dict(ticket)
            in_progress_items.append(ticket_dict)
        elif ticket.status in ('done', 'closed'):
            # Check if updated_at is within the 7-day window
            ticket_updated_date = ticket.updated_at.date()
            if window_start <= ticket_updated_date <= today:
                completed_items.append(ticket)
    
    # Sort todo and in_progress by created_at oldest first
    todo_items.sort(key=lambda t: t['created_at'])
    in_progress_items.sort(key=lambda t: t['created_at'])
    
    # Sort completed by updated_at newest first
    completed_items.sort(key=lambda t: t.updated_at, reverse=True)
    completed = [ticket_to_dict(t) for t in completed_items]
    
    return {
        'todo': todo_items,
        'in_progress': in_progress_items,
        'completed': completed
    }


def summary(session, user: str, today: date) -> dict:
    """Get a summary of tickets for a user.
    
    Args:
        session: Database session
        user: The user to get summary for ('her' or 'him')
        today: The reference date for overdue/due_today calculations
    
    Returns:
        Dict with keys 'overdue', 'due_today', 'open' containing counts.
        - open: count of all tickets assigned to user with status not done/closed
        - overdue: count of those due before today
        - due_today: count of those due exactly today
    """
    # Get all tickets assigned to this user that are not done or closed
    stmt = select(Ticket).where(
        and_(
            Ticket.assigned_to == user,
            Ticket.status.notin_(['done', 'closed'])
        )
    )
    tickets = session.execute(stmt).scalars().all()
    
    open_count = len(tickets)
    overdue_count = 0
    due_today_count = 0
    
    for ticket in tickets:
        if ticket.due is not None:
            if ticket.due < today:
                overdue_count += 1
            elif ticket.due == today:
                due_today_count += 1
    
    return {
        'overdue': overdue_count,
        'due_today': due_today_count,
        'open': open_count
    }
    """Get the household board with all tickets from both users.
    
    Args:
        session: Database session
        today: The reference date for the completed window
    
    Returns:
        Dict with keys 'todo', 'in_progress', 'completed', each a list of
        ticket_to_dict dicts (no 'group' key).
    """
    # Get all tickets from both users
    stmt = select(Ticket)
    tickets = session.execute(stmt).scalars().all()
    
    todo_items = []
    in_progress_items = []
    completed_items = []
    
    # Calculate the 7-day window for completed (today + 6 days before)
    window_start = today - timedelta(days=6)
    
    for ticket in tickets:
        if ticket.status in ('open', 'acknowledged'):
            # Todo column
            ticket_dict = ticket_to_dict(ticket)
            todo_items.append(ticket_dict)
        elif ticket.status == 'in_progress':
            # In progress column
            ticket_dict = ticket_to_dict(ticket)
            in_progress_items.append(ticket_dict)
        elif ticket.status in ('done', 'closed'):
            # Check if updated_at is within the 7-day window
            ticket_updated_date = ticket.updated_at.date()
            if window_start <= ticket_updated_date <= today:
                completed_items.append(ticket)
    
    # Sort todo and in_progress by created_at oldest first
    todo_items.sort(key=lambda t: t['created_at'])
    in_progress_items.sort(key=lambda t: t['created_at'])
    
    # Sort completed by updated_at newest first
    completed_items.sort(key=lambda t: t.updated_at, reverse=True)
    completed = [ticket_to_dict(t) for t in completed_items]
    
    return {
        'todo': todo_items,
        'in_progress': in_progress_items,
        'completed': completed
    }
