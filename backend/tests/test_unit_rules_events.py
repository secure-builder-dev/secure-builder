import pytest

from app.rules import create_ticket, change_status
from app.models import Ticket, TicketEvent


def test_create_ticket_records_event(db):
    """A successful create_ticket should record a 'filed' event.
    The event must have the filer as actor, from_status None and to_status 'open',
    and be persisted in the same commit as the ticket.
    """
    # Act: create a ticket
    ticket_dict = create_ticket(db, "her", {"title": "Test ticket"})

    # Assert: ticket exists
    ticket = db.get(Ticket, ticket_dict["id"])  # type: ignore[arg-type]
    assert ticket is not None
    # Assert: exactly one event recorded for this ticket
    events = db.query(TicketEvent).filter(TicketEvent.ticket_id == ticket.id).all()
    assert len(events) == 1
    ev = events[0]
    assert ev.kind == "filed"
    assert ev.actor == "her"
    assert ev.from_status is None
    assert ev.to_status == "open"


def test_create_ticket_invalid_filer_no_event(db):
    """When create_ticket raises, no ticket or event should be persisted.
    This ensures that a failing call does not leave stray records.
    """
    from app.models import TicketEvent
    # Act & Assert: invalid filer raises ValueError
    with pytest.raises(ValueError):
        create_ticket(db, "invalid_user", {"title": "Bad"})
    # No tickets created
    assert db.query(Ticket).count() == 0
    # No events recorded
    assert db.query(TicketEvent).count() == 0


def test_change_status_records_event(db):
    """A successful status change should record a 'status' event.
    The event must contain the caller as actor, the old status and the new status.
    """
    # Arrange: create a ticket filed by her (assigned to him)
    ticket_dict = create_ticket(db, "her", {"title": "Status test"})
    ticket_id = ticket_dict["id"]
    # Act: assignee (him) moves from open -> acknowledged
    updated = change_status(db, ticket_id, "him", "acknowledged")
    # Assert ticket status updated
    assert updated["status"] == "acknowledged"
    # Assert exactly two events now (filed + status)
    events = db.query(TicketEvent).filter(TicketEvent.ticket_id == ticket_id).order_by(TicketEvent.id).all()
    assert len(events) == 2
    filed_ev, status_ev = events
    # Filed event unchanged
    assert filed_ev.kind == "filed"
    # Status event checks
    assert status_ev.kind == "status"
    assert status_ev.actor == "him"
    assert status_ev.from_status == "open"
    assert status_ev.to_status == "acknowledged"


def test_change_status_invalid_transition_no_event(db):
    """When change_status raises due to an invalid transition, no new event is recorded.
    Only the original 'filed' event should remain.
    """
    ticket_dict = create_ticket(db, "her", {"title": "Bad transition"})
    ticket_id = ticket_dict["id"]
    # Attempt invalid transition: open -> in_progress (skipping acknowledged)
    with pytest.raises(ValueError):
        change_status(db, ticket_id, "him", "in_progress")
    # Verify only the filed event exists
    events = db.query(TicketEvent).filter(TicketEvent.ticket_id == ticket_id).all()
    assert len(events) == 1
    assert events[0].kind == "filed"


def test_change_status_permission_error_no_event(db):
    """When change_status raises PermissionError, no additional event is recorded.
    The caller must be the correct party; otherwise the operation fails silently regarding events.
    """
    ticket_dict = create_ticket(db, "her", {"title": "Permission test"})
    ticket_id = ticket_dict["id"]
    # Filer (her) tries to perform assignee‑only transition
    with pytest.raises(PermissionError):
        change_status(db, ticket_id, "her", "acknowledged")
    # Only the original filed event should be present
    events = db.query(TicketEvent).filter(TicketEvent.ticket_id == ticket_id).all()
    assert len(events) == 1
    assert events[0].kind == "filed"
