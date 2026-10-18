import datetime
import pytest
from app.rules import create_ticket, change_status, ticket_to_dict
from app.models import Ticket


def test_change_status_successful_moves(db):
    # Create a ticket filed by 'her' (assigned to 'him')
    ticket_dict = create_ticket(db, "her", {"title": "Test"})
    ticket_id = ticket_dict["id"]
    # 1. open -> acknowledged by assignee (him)
    result = change_status(db, ticket_id, "him", "acknowledged")
    assert result["status"] == "acknowledged"
    # 2. acknowledged -> in_progress by assignee (him)
    result = change_status(db, ticket_id, "him", "in_progress")
    assert result["status"] == "in_progress"
    # 3. in_progress -> done by assignee (him)
    result = change_status(db, ticket_id, "him", "done")
    assert result["status"] == "done"
    # 4. done -> closed by filer (her)
    result = change_status(db, ticket_id, "her", "closed")
    assert result["status"] == "closed"
    # 5. closed -> open (reopen) by filer (her)
    result = change_status(db, ticket_id, "her", "open")
    assert result["status"] == "open"
    # Verify updated_at changed after each successful move
    ticket_obj = db.get(Ticket, ticket_id)
    assert ticket_obj.updated_at.tzinfo is not None


def test_change_status_lookup_error_missing_ticket(db):
    with pytest.raises(LookupError):
        change_status(db, 9999, "her", "acknowledged")


def test_change_status_lookup_error_non_party_user(db):
    ticket_dict = create_ticket(db, "her", {"title": "Test"})
    ticket_id = ticket_dict["id"]
    # 'other' is not a valid user and not a party
    with pytest.raises(LookupError):
        change_status(db, ticket_id, "other", "acknowledged")


def test_change_status_value_error_invalid_status(db):
    ticket_dict = create_ticket(db, "her", {"title": "Test"})
    ticket_id = ticket_dict["id"]
    with pytest.raises(ValueError):
        change_status(db, ticket_id, "him", "invalid_status")


def test_change_status_value_error_invalid_transition(db):
    ticket_dict = create_ticket(db, "her", {"title": "Test"})
    ticket_id = ticket_dict["id"]
    # Attempt open -> done directly, which is not allowed
    with pytest.raises(ValueError):
        change_status(db, ticket_id, "him", "done")


def test_change_status_permission_error_wrong_user(db):
    ticket_dict = create_ticket(db, "her", {"title": "Test"})
    ticket_id = ticket_dict["id"]
    # Filer (her) tries to perform assignee transition
    with pytest.raises(PermissionError):
        change_status(db, ticket_id, "her", "acknowledged")


def test_change_status_no_change_on_error(db):
    ticket_dict = create_ticket(db, "her", {"title": "Test"})
    ticket_id = ticket_dict["id"]
    ticket_before = db.get(Ticket, ticket_id)
    created_at = ticket_before.created_at
    updated_at = ticket_before.updated_at
    # Attempt invalid transition which raises ValueError
    try:
        change_status(db, ticket_id, "him", "done")
    except ValueError:
        pass
    ticket_after = db.get(Ticket, ticket_id)
    assert ticket_after.status == "open"
    assert ticket_after.created_at == created_at
    assert ticket_after.updated_at == updated_at
