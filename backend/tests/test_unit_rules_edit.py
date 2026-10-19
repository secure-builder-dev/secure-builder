import pytest
import datetime
from app import rules
from app.models import Ticket, TicketEvent


# Clause 1: error order and types
def test_edit_ticket_error_order(db):
    # baseline ticket filed by 'her'
    ticket = rules.create_ticket(db, "her", {"title": "Initial", "details": "", "priority": "normal"})
    ticket_id = ticket["id"]

    # 1a) LookupError when ticket does not exist
    with pytest.raises(LookupError):
        rules.edit_ticket(db, 9999, "her", {"title": "New"})

    # 1b) LookupError when user is not a party
    with pytest.raises(LookupError):
        rules.edit_ticket(db, ticket_id, "other", {"title": "New"})

    # 1c) ValueError when data is not a dict
    with pytest.raises(ValueError):
        rules.edit_ticket(db, ticket_id, "her", "not a dict")

    # 1d) ValueError when data is empty dict
    with pytest.raises(ValueError):
        rules.edit_ticket(db, ticket_id, "her", {})

    # 1e) ValueError when data contains an unexpected key
    with pytest.raises(ValueError):
        rules.edit_ticket(db, ticket_id, "her", {"foo": "bar"})

    # 1f) ValueError when a value would be rejected by create_ticket (title too long)
    long_title = "x" * 121
    with pytest.raises(ValueError):
        rules.edit_ticket(db, ticket_id, "her", {"title": long_title})

    # 1g) PermissionError when user is not the filer (assignee tries to edit)
    # The ticket is assigned to "him" (the other user) by create_ticket
    with pytest.raises(PermissionError):
        rules.edit_ticket(db, ticket_id, "him", {"title": "New"})

    # 1h) NotEditable when status is not open or acknowledged
    # Move ticket to in_progress first (allowed transition by assignee)
    rules.change_status(db, ticket_id, "him", "acknowledged")
    rules.change_status(db, ticket_id, "him", "in_progress")
    with pytest.raises(rules.NotEditable):
        rules.edit_ticket(db, ticket_id, "her", {"title": "New"})


def test_noteditable_subclass():
    assert issubclass(rules.NotEditable, Exception)
    assert not issubclass(rules.NotEditable, ValueError)
    assert not issubclass(rules.NotEditable, PermissionError)


# Clause 3: successful edit behavior
def test_successful_edit_changes_fields_and_records_event(db):
    ticket = rules.create_ticket(db, "her", {"title": "Initial", "details": "", "priority": "normal"})
    ticket_id = ticket["id"]
    original = db.get(Ticket, ticket_id)
    original_updated = original.updated_at

    result = rules.edit_ticket(
        db,
        ticket_id,
        "her",
        {"title": "  New Title  ", "details": "New details"},
    )

    # Verify returned dict reflects changes
    assert result["title"] == "New Title"
    assert result["details"] == "New details"
    # Verify other fields unchanged
    assert result["priority"] == original.priority
    assert result["due"] == (original.due.isoformat() if original.due else None)
    # Verify updated_at changed
    assert result["updated_at"] != original_updated.isoformat()
    # Verify database reflects changes
    refreshed = db.get(Ticket, ticket_id)
    assert refreshed.title == "New Title"
    assert refreshed.details == "New details"
    # Verify an 'edited' event was recorded
    events = (
        db.query(TicketEvent)
        .filter(TicketEvent.ticket_id == ticket_id, TicketEvent.kind == "edited")
        .all()
    )
    assert len(events) == 1
    ev = events[0]
    assert ev.actor == "her"
    assert ev.from_status is None
    assert ev.to_status is None
    # Ensure the transaction was committed (event persisted)
    db.commit()


# Clause 4: failed edit makes no changes and records nothing
def test_failed_edit_no_change_no_event(db):
    ticket = rules.create_ticket(db, "her", {"title": "Initial", "details": "", "priority": "normal"})
    ticket_id = ticket["id"]
    before_events = (
        db.query(TicketEvent)
        .filter(TicketEvent.ticket_id == ticket_id)
        .count()
    )
    long_title = "x" * 121
    with pytest.raises(ValueError):
        rules.edit_ticket(db, ticket_id, "her", {"title": long_title})
    # Verify ticket unchanged
    refreshed = db.get(Ticket, ticket_id)
    assert refreshed.title == "Initial"
    # Verify no new events recorded
    after_events = (
        db.query(TicketEvent)
        .filter(TicketEvent.ticket_id == ticket_id)
        .count()
    )
    assert before_events == after_events
