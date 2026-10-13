import pytest
from datetime import datetime, timezone, date

from app.rules import ticket_to_dict, create_ticket
from app.models import Ticket


class TestTicketToDict:
    def test_returns_plain_dict_with_all_columns(self, db):
        ticket = Ticket(
            id=1,
            title="Test",
            details="Details",
            priority="normal",
            due=datetime(2024, 1, 15),
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        )
        result = ticket_to_dict(ticket)
        assert isinstance(result, dict)
        assert "id" in result
        assert "title" in result
        assert "details" in result
        assert "priority" in result
        assert "due" in result
        assert "status" in result
        assert "filed_by" in result
        assert "assigned_to" in result
        assert "created_at" in result
        assert "updated_at" in result

    def test_due_as_yyyy_mm_dd_string(self, db):
        ticket = Ticket(
            id=1,
            title="Test",
            details="",
            priority="normal",
            due=datetime(2024, 3, 5),
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        result = ticket_to_dict(ticket)
        assert result["due"] == "2024-03-05"

    def test_due_none_when_null(self, db):
        ticket = Ticket(
            id=1,
            title="Test",
            details="",
            priority="normal",
            due=None,
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        result = ticket_to_dict(ticket)
        assert result["due"] is None

    def test_created_at_as_iso8601(self, db):
        now = datetime(2024, 7, 20, 15, 30, 45, tzinfo=timezone.utc)
        ticket = Ticket(
            id=1,
            title="Test",
            details="",
            priority="normal",
            due=None,
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=now,
            updated_at=now,
        )
        result = ticket_to_dict(ticket)
        assert "2024-07-20T15:30:45+00:00" in result["created_at"]

    def test_updated_at_as_iso8601(self, db):
        now = datetime(2024, 7, 20, 15, 30, 45, tzinfo=timezone.utc)
        ticket = Ticket(
            id=1,
            title="Test",
            details="",
            priority="normal",
            due=None,
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=now,
            updated_at=now,
        )
        result = ticket_to_dict(ticket)
        assert "2024-07-20T15:30:45+00:00" in result["updated_at"]


class TestCreateTicketValidation:
    def test_raises_value_error_when_filed_by_not_in_users(self, db):
        with pytest.raises(ValueError):
            create_ticket(db, "them", {"title": "Test"})

    def test_raises_value_error_when_data_holds_extra_key(self, db):
        with pytest.raises(ValueError):
            create_ticket(db, "her", {"title": "Test", "status": "open"})

    def test_title_required(self, db):
        with pytest.raises(ValueError):
            create_ticket(db, "her", {})

    def test_title_must_be_str(self, db):
        with pytest.raises(ValueError):
            create_ticket(db, "her", {"title": 123})

    def test_title_stripped_and_1_to_120_chars(self, db):
        # Too short after stripping
        with pytest.raises(ValueError):
            create_ticket(db, "her", {"title": "   "})
        # Exactly 1 char after stripping
        result = create_ticket(db, "her", {"title": " a "})
        assert result["title"] == "a"
        # Too long after stripping (121 chars)
        with pytest.raises(ValueError):
            create_ticket(db, "her", {"title": "x" * 121})

    def test_title_stored_stripped(self, db):
        result = create_ticket(db, "her", {"title": "  Hello World  "})
        assert result["title"] == "Hello World"

    def test_details_optional_str_max_1000_chars(self, db):
        # Default empty string
        result = create_ticket(db, "her", {"title": "Test"})
        assert result["details"] == ""
        # Valid details
        result = create_ticket(db, "her", {"title": "Test", "details": "Some details"})
        assert result["details"] == "Some details"
        # Too long (1001 chars)
        with pytest.raises(ValueError):
            create_ticket(db, "her", {"title": "Test", "details": "x" * 1001})

    def test_details_must_be_str(self, db):
        with pytest.raises(ValueError):
            create_ticket(db, "her", {"title": "Test", "details": 123})

    def test_priority_optional_default_normal(self, db):
        result = create_ticket(db, "her", {"title": "Test"})
        assert result["priority"] == "normal"

    def test_priority_must_be_one_of_low_normal_urgent(self, db):
        for p in ["low", "normal", "urgent"]:
            result = create_ticket(db, "her", {"title": "Test", "priority": p})
            assert result["priority"] == p
        with pytest.raises(ValueError):
            create_ticket(db, "her", {"title": "Test", "priority": "high"})

    def test_priority_must_be_str(self, db):
        with pytest.raises(ValueError):
            create_ticket(db, "her", {"title": "Test", "priority": 1})

    def test_due_optional_default_none(self, db):
        result = create_ticket(db, "her", {"title": "Test"})
        assert result["due"] is None

    def test_due_must_be_yyyy_mm_dd_real_date(self, db):
        # Valid date
        result = create_ticket(db, "her", {"title": "Test", "due": "2024-12-25"})
        assert result["due"] == "2024-12-25"
        # Invalid date (Feb 30)
        with pytest.raises(ValueError):
            create_ticket(db, "her", {"title": "Test", "due": "2024-02-30"})
        # Invalid format
        with pytest.raises(ValueError):
            create_ticket(db, "her", {"title": "Test", "due": "12-25-2024"})

    def test_due_must_be_str_or_none(self, db):
        with pytest.raises(ValueError):
            create_ticket(db, "her", {"title": "Test", "due": datetime(2024, 1, 1)})

    def test_nothing_stored_on_validation_error(self, db):
        initial_count = db.query(Ticket).count()
        with pytest.raises(ValueError):
            create_ticket(db, "her", {"title": "x" * 121})
        final_count = db.query(Ticket).count()
        assert initial_count == final_count


class TestCreateTicketSuccess:
    def test_status_is_open(self, db):
        result = create_ticket(db, "her", {"title": "Test"})
        assert result["status"] == "open"

    def test_assigned_to_other_user(self, db):
        result_her = create_ticket(db, "her", {"title": "Test1"})
        assert result_her["assigned_to"] == "him"
        result_him = create_ticket(db, "him", {"title": "Test2"})
        assert result_him["assigned_to"] == "her"

    def test_created_at_and_updated_at_same_utc_time(self, db):
        result = create_ticket(db, "her", {"title": "Test"})
        created = datetime.fromisoformat(result["created_at"])
        updated = datetime.fromisoformat(result["updated_at"])
        assert created.tzinfo is not None
        assert updated.tzinfo is not None
        assert created.replace(microsecond=0) == updated.replace(microsecond=0)

    def test_ticket_committed_to_db(self, db):
        result = create_ticket(db, "her", {"title": "Test"})
        ticket = db.query(Ticket).filter_by(id=result["id"]).first()
        assert ticket is not None
        assert ticket.title == "Test"

    def test_returns_ticket_to_dict(self, db):
        result = create_ticket(db, "her", {"title": "Test", "details": "D", "priority": "urgent", "due": "2024-01-01"})
        assert isinstance(result, dict)
        assert result["title"] == "Test"
        assert result["details"] == "D"
        assert result["priority"] == "urgent"
        assert result["due"] == "2024-01-01"
        assert result["status"] == "open"
        assert result["filed_by"] == "her"
        assert result["assigned_to"] == "him"
        assert "created_at" in result
        assert "updated_at" in result
