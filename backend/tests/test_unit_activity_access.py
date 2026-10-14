"""Tests for activity module access control.

These tests verify that the activity functions properly reject requests from users
who are not parties to a ticket (i.e., not the filer or assignee).
"""
import pytest
from app.activity import list_comments, ticket_history, add_comment
from app.models import Ticket
from datetime import datetime, timezone


class TestActivityAccessControl:
    """Test that activity functions reject non-parties."""

    def test_list_comments_rejects_non_party(self, db):
        """list_comments raises LookupError for a user who is not a party."""
        # Create a ticket filed by her, assigned to him
        ticket = Ticket(
            title="Test ticket",
            details="Test details",
            priority="normal",
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(ticket)
        db.commit()
        db.refresh(ticket)

        # A stranger should not be able to list comments
        with pytest.raises(LookupError):
            list_comments(db, ticket.id, "stranger")

    def test_ticket_history_rejects_non_party(self, db):
        """ticket_history raises LookupError for a user who is not a party."""
        # Create a ticket filed by her, assigned to him
        ticket = Ticket(
            title="Test ticket",
            details="Test details",
            priority="normal",
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(ticket)
        db.commit()
        db.refresh(ticket)

        # A stranger should not be able to read history
        with pytest.raises(LookupError):
            ticket_history(db, ticket.id, "stranger")

    def test_add_comment_rejects_non_party(self, db):
        """add_comment raises LookupError for a user who is not a party."""
        # Create a ticket filed by her, assigned to him
        ticket = Ticket(
            title="Test ticket",
            details="Test details",
            priority="normal",
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(ticket)
        db.commit()
        db.refresh(ticket)

        # A stranger should not be able to add comments
        with pytest.raises(LookupError):
            add_comment(db, ticket.id, "stranger", "Test comment")


class TestActivityApiAccessControl:
    """Test that activity API endpoints reject unauthenticated requests."""

    def test_other_user_cannot_read_comments(self, client, tables):
        """GET /api/tickets/{id}/comments with BAD token returns 401."""
        from tests.conftest import HER, BAD
        
        # Create a ticket with HER
        response = client.post(
            "/api/tickets",
            headers=HER,
            json={"title": "Test ticket", "priority": "normal"}
        )
        assert response.status_code == 201
        ticket_id = response.json()["id"]

        # Try to read comments with BAD token (unauthorized)
        response = client.get(
            f"/api/tickets/{ticket_id}/comments",
            headers=BAD
        )
        assert response.status_code == 401

    def test_other_user_cannot_add_comments(self, client, tables):
        """POST /api/tickets/{id}/comments with BAD token returns 401 and does not add comment."""
        from tests.conftest import HER, BAD
        
        # Create a ticket with HER
        response = client.post(
            "/api/tickets",
            headers=HER,
            json={"title": "Test ticket", "priority": "normal"}
        )
        assert response.status_code == 201
        ticket_id = response.json()["id"]

        # Try to add a comment with BAD token (unauthorized)
        response = client.post(
            f"/api/tickets/{ticket_id}/comments",
            headers=BAD,
            json={"body": "x"}
        )
        assert response.status_code == 401

        # Verify the comment was not added by reading with HER
        response = client.get(
            f"/api/tickets/{ticket_id}/comments",
            headers=HER
        )
        assert response.status_code == 200
        assert response.json()["comments"] == []

    def test_other_user_cannot_read_history(self, client, tables):
        """GET /api/tickets/{id}/history with BAD token returns 401."""
        from tests.conftest import HER, BAD
        
        # Create a ticket with HER
        response = client.post(
            "/api/tickets",
            headers=HER,
            json={"title": "Test ticket", "priority": "normal"}
        )
        assert response.status_code == 201
        ticket_id = response.json()["id"]

        # Try to read history with BAD token (unauthorized)
        response = client.get(
            f"/api/tickets/{ticket_id}/history",
            headers=BAD
        )
        assert response.status_code == 401
