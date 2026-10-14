import pytest
from datetime import datetime, timezone
from datetime import datetime, timezone, date

from app.rules import USERS, ticket_to_dict, create_ticket
from app.models import Ticket


class TestUsersConstant:
    """Clause 1: USERS = ('her', 'him')"""

    def test_users_is_tuple_with_her_and_him(self):
        assert USERS == ('her', 'him')


class TestTicketToDict:
    """Clause 1: ticket_to_dict returns plain dict with correct formats"""

    def test_ticket_to_dict_returns_plain_dict(self, db):
        from datetime import datetime, timezone
        
        now = datetime.now(timezone.utc)
        ticket = Ticket(
            title="Test",
            details="Details",
            priority="normal",
            due=None,
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=now,
            updated_at=now
        )
        db.add(ticket)
        db.flush()
        
        result = ticket_to_dict(ticket)
        assert isinstance(result, dict)
        assert not isinstance(result, Ticket)

    def test_ticket_to_dict_includes_all_columns(self, db):
        from datetime import datetime, timezone
        
        now = datetime.now(timezone.utc)
        ticket = Ticket(
            title="Test",
            details="Details",
            priority="normal",
            due=None,
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=now,
            updated_at=now
        )
        db.add(ticket)
        db.flush()
        
        result = ticket_to_dict(ticket)
        assert set(result.keys()) == {
            'id', 'title', 'details', 'priority', 'due',
            'status', 'filed_by', 'assigned_to', 'created_at', 'updated_at'
        }

    def test_ticket_to_dict_due_as_yyyy_mm_dd_string(self, db):
        from datetime import date, datetime, timezone
        
        now = datetime.now(timezone.utc)
        due_date = date(2025, 12, 25)
        ticket = Ticket(
            title="Test",
            details="Details",
            priority="normal",
            due=due_date,
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=now,
            updated_at=now
        )
        db.add(ticket)
        db.flush()
        
        result = ticket_to_dict(ticket)
        assert result['due'] == "2025-12-25"

    def test_ticket_to_dict_due_none_when_null(self, db):
        from datetime import datetime, timezone
        
        now = datetime.now(timezone.utc)
        ticket = Ticket(
            title="Test",
            details="Details",
            priority="normal",
            due=None,
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=now,
            updated_at=now
        )
        db.add(ticket)
        db.flush()
        
        result = ticket_to_dict(ticket)
        assert result['due'] is None

    def test_ticket_to_dict_created_at_as_iso8601(self, db):
        from datetime import datetime, timezone
        
        now = datetime(2025, 1, 15, 10, 30, 45, tzinfo=timezone.utc)
        ticket = Ticket(
            title="Test",
            details="Details",
            priority="normal",
            due=None,
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=now,
            updated_at=now
        )
        db.add(ticket)
        db.flush()
        
        result = ticket_to_dict(ticket)
        assert '2025-01-15T10:30:45+00:00' in result['created_at']

    def test_ticket_to_dict_updated_at_as_iso8601(self, db):
        from datetime import datetime, timezone
        
        now = datetime(2025, 1, 15, 10, 30, 45, tzinfo=timezone.utc)
        ticket = Ticket(
            title="Test",
            details="Details",
            priority="normal",
            due=None,
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=now,
            updated_at=now
        )
        db.add(ticket)
        db.flush()
        
        result = ticket_to_dict(ticket)
        assert '2025-01-15T10:30:45+00:00' in result['updated_at']


class TestCreateTicketFiledByValidation:
    """Clause 2: filed_by must be in USERS"""

    def test_create_ticket_raises_value_error_when_filed_by_not_in_users(self, db):
        data = {"title": "Test ticket"}
        with pytest.raises(ValueError):
            create_ticket(db, "invalid_user", data)

    def test_create_ticket_accepts_her_as_filed_by(self, db):
        data = {"title": "Test ticket"}
        result = create_ticket(db, "her", data)
        assert result['filed_by'] == 'her'

    def test_create_ticket_accepts_him_as_filed_by(self, db):
        data = {"title": "Test ticket"}
        result = create_ticket(db, "him", data)
        assert result['filed_by'] == 'him'


class TestCreateTicketDataKeysValidation:
    """Clause 2: data may hold only title, details, priority, due"""

    def test_create_ticket_raises_value_error_when_data_has_extra_key(self, db):
        data = {"title": "Test", "invalid_key": "value"}
        with pytest.raises(ValueError):
            create_ticket(db, "her", data)

    def test_create_ticket_accepts_only_title(self, db):
        data = {"title": "Test ticket"}
        result = create_ticket(db, "her", data)
        assert result['title'] == 'Test ticket'

    def test_create_ticket_accepts_all_valid_keys(self, db):
        data = {
            "title": "Test",
            "details": "Some details",
            "priority": "urgent",
            "due": "2025-12-25"
        }
        result = create_ticket(db, "her", data)
        assert result['title'] == 'Test'
        assert result['details'] == 'Some details'
        assert result['priority'] == 'urgent'
        assert result['due'] == '2025-12-25'


class TestCreateTicketTitleValidation:
    """Clause 3: title required, str, 1-120 chars after stripping"""

    def test_create_ticket_raises_value_error_when_title_missing(self, db):
        data = {}
        with pytest.raises(ValueError):
            create_ticket(db, "her", data)

    def test_create_ticket_raises_value_error_when_title_not_str(self, db):
        data = {"title": 123}
        with pytest.raises(ValueError):
            create_ticket(db, "her", data)

    def test_create_ticket_raises_value_error_when_title_empty_after_stripping(self, db):
        data = {"title": "   "}
        with pytest.raises(ValueError):
            create_ticket(db, "her", data)

    def test_create_ticket_raises_value_error_when_title_over_120_chars(self, db):
        data = {"title": "x" * 121}
        with pytest.raises(ValueError):
            create_ticket(db, "her", data)

    def test_create_ticket_strips_title_whitespace(self, db):
        data = {"title": "  Test ticket  "}
        result = create_ticket(db, "her", data)
        assert result['title'] == 'Test ticket'

    def test_create_ticket_accepts_title_1_char(self, db):
        data = {"title": "x"}
        result = create_ticket(db, "her", data)
        assert result['title'] == 'x'

    def test_create_ticket_accepts_title_120_chars(self, db):
        data = {"title": "x" * 120}
        result = create_ticket(db, "her", data)
        assert len(result['title']) == 120


class TestCreateTicketDetailsValidation:
    """Clause 3: details optional str, max 1000 chars, default ''"""

    def test_create_ticket_details_defaults_to_empty_string(self, db):
        data = {"title": "Test"}
        result = create_ticket(db, "her", data)
        assert result['details'] == ''

    def test_create_ticket_raises_value_error_when_details_not_str(self, db):
        data = {"title": "Test", "details": 123}
        with pytest.raises(ValueError):
            create_ticket(db, "her", data)

    def test_create_ticket_raises_value_error_when_details_over_1000_chars(self, db):
        data = {"title": "Test", "details": "x" * 1001}
        with pytest.raises(ValueError):
            create_ticket(db, "her", data)

    def test_create_ticket_accepts_details_1000_chars(self, db):
        data = {"title": "Test", "details": "x" * 1000}
        result = create_ticket(db, "her", data)
        assert len(result['details']) == 1000


class TestCreateTicketPriorityValidation:
    """Clause 3: priority optional, one of low/normal/urgent, default normal"""

    def test_create_ticket_priority_defaults_to_normal(self, db):
        data = {"title": "Test"}
        result = create_ticket(db, "her", data)
        assert result['priority'] == 'normal'

    def test_create_ticket_raises_value_error_when_priority_not_str(self, db):
        data = {"title": "Test", "priority": 123}
        with pytest.raises(ValueError):
            create_ticket(db, "her", data)

    def test_create_ticket_raises_value_error_when_priority_invalid(self, db):
        data = {"title": "Test", "priority": "high"}
        with pytest.raises(ValueError):
            create_ticket(db, "her", data)

    def test_create_ticket_accepts_priority_low(self, db):
        data = {"title": "Test", "priority": "low"}
        result = create_ticket(db, "her", data)
        assert result['priority'] == 'low'

    def test_create_ticket_accepts_priority_normal(self, db):
        data = {"title": "Test", "priority": "normal"}
        result = create_ticket(db, "her", data)
        assert result['priority'] == 'normal'

    def test_create_ticket_accepts_priority_urgent(self, db):
        data = {"title": "Test", "priority": "urgent"}
        result = create_ticket(db, "her", data)
        assert result['priority'] == 'urgent'


class TestCreateTicketDueValidation:
    """Clause 3: due optional, None or YYYY-MM-DD real date, default None"""

    def test_create_ticket_due_defaults_to_none(self, db):
        data = {"title": "Test"}
        result = create_ticket(db, "her", data)
        assert result['due'] is None

    def test_create_ticket_accepts_due_as_none(self, db):
        data = {"title": "Test", "due": None}
        result = create_ticket(db, "her", data)
        assert result['due'] is None

    def test_create_ticket_raises_value_error_when_due_not_str_or_none(self, db):
        data = {"title": "Test", "due": 123}
        with pytest.raises(ValueError):
            create_ticket(db, "her", data)

    def test_create_ticket_raises_value_error_when_due_invalid_format(self, db):
        data = {"title": "Test", "due": "2025/12/25"}
        with pytest.raises(ValueError):
            create_ticket(db, "her", data)

    def test_create_ticket_raises_value_error_when_due_not_real_date(self, db):
        data = {"title": "Test", "due": "2025-02-30"}
        with pytest.raises(ValueError):
            create_ticket(db, "her", data)

    def test_create_ticket_accepts_valid_due_date(self, db):
        data = {"title": "Test", "due": "2025-12-25"}
        result = create_ticket(db, "her", data)
        assert result['due'] == '2025-12-25'


class TestCreateTicketSuccessBehavior:
    """Clause 4: status open, assigned to other user, timestamps set, committed, returned"""

    def test_create_ticket_sets_status_to_open(self, db):
        data = {"title": "Test"}
        result = create_ticket(db, "her", data)
        assert result['status'] == 'open'

    def test_create_ticket_assigns_to_other_user_when_filed_by_her(self, db):
        data = {"title": "Test"}
        result = create_ticket(db, "her", data)
        assert result['assigned_to'] == 'him'

    def test_create_ticket_assigns_to_other_user_when_filed_by_him(self, db):
        data = {"title": "Test"}
        result = create_ticket(db, "him", data)
        assert result['assigned_to'] == 'her'

    def test_create_ticket_sets_created_at_and_updated_at_to_same_time(self, db):
        data = {"title": "Test"}
        result = create_ticket(db, "her", data)
        # Both should be ISO-8601 strings and equal
        assert result['created_at'] == result['updated_at']

    def test_create_ticket_sets_timezone_aware_utc_timestamps(self, db):
        data = {"title": "Test"}
        result = create_ticket(db, "her", data)
        
        # Parse the ISO-8601 string and check it's timezone aware
        created = datetime.fromisoformat(result['created_at'])
        assert created.tzinfo is not None
        assert created.tzinfo.utcoffset(created).total_seconds() == 0

    def test_create_ticket_is_committed_to_database(self, db):
        data = {"title": "Test"}
        result = create_ticket(db, "her", data)
        ticket_id = result['id']
        
        # Force a new session to verify commit
        db.expunge_all()
        found = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        assert found is not None
        assert found.title == 'Test'

    def test_create_ticket_returns_ticket_to_dict_format(self, db):
        data = {"title": "Test", "details": "Details", "priority": "urgent", "due": "2025-12-25"}
        result = create_ticket(db, "her", data)
        
        assert isinstance(result, dict)
        assert 'id' in result
        assert 'title' in result
        assert 'details' in result
        assert 'priority' in result
        assert 'due' in result
        assert 'status' in result
        assert 'filed_by' in result
        assert 'assigned_to' in result
        assert 'created_at' in result
        assert 'updated_at' in result
        
        # Verify formats
        assert isinstance(result['title'], str)
        assert isinstance(result['details'], str)
        assert isinstance(result['priority'], str)
        assert result['due'] == '2025-12-25'
        assert isinstance(result['created_at'], str)
        assert isinstance(result['updated_at'], str)
