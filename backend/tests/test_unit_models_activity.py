import pytest
from sqlalchemy import inspect

from app.db import SessionLocal, init_db, engine
from app.models import Ticket, Comment, TicketEvent


class TestCommentModel:
    """Tests for the Comment model definition."""

    def test_comment_has_correct_table_name(self):
        """Comment table name is 'comments'."""
        assert Comment.__tablename__ == "comments"

    def test_comment_has_id_column_as_primary_key(self):
        """Comment has id column as Integer primary key."""
        mapper = Comment.__mapper__
        id_column = mapper.columns.get("id")
        assert id_column is not None
        assert id_column.primary_key

    def test_comment_has_ticket_id_as_foreign_key(self):
        """Comment has ticket_id as Integer ForeignKey to tickets.id."""
        mapper = Comment.__mapper__
        ticket_id_column = mapper.columns.get("ticket_id")
        assert ticket_id_column is not None
        # Check that it's a foreign key to tickets.id
        assert len(ticket_id_column.foreign_keys) == 1
        fk = list(ticket_id_column.foreign_keys)[0]
        assert fk.column.table.name == "tickets"
        assert fk.column.name == "id"

    def test_comment_has_author_column(self):
        """Comment has author column as String."""
        mapper = Comment.__mapper__
        author_column = mapper.columns.get("author")
        assert author_column is not None

    def test_comment_has_body_column_with_length_500(self):
        """Comment has body column as String(500)."""
        mapper = Comment.__mapper__
        body_column = mapper.columns.get("body")
        assert body_column is not None
        # Check the length constraint
        assert hasattr(body_column.type, "length")
        assert body_column.type.length == 500

    def test_comment_has_created_at_column_with_timezone(self):
        """Comment has created_at column as DateTime(timezone=True)."""
        mapper = Comment.__mapper__
        created_at_column = mapper.columns.get("created_at")
        assert created_at_column is not None
        assert hasattr(created_at_column.type, "timezone")
        assert created_at_column.type.timezone is True

    def test_comment_has_exactly_the_required_columns(self):
        """Comment has exactly id, ticket_id, author, body, created_at."""
        mapper = Comment.__mapper__
        column_names = {col.name for col in mapper.columns}
        expected = {"id", "ticket_id", "author", "body", "created_at"}
        assert column_names == expected


class TestTicketEventModel:
    """Tests for the TicketEvent model definition."""

    def test_ticket_event_has_correct_table_name(self):
        """TicketEvent table name is 'ticket_events'."""
        assert TicketEvent.__tablename__ == "ticket_events"

    def test_ticket_event_has_id_column_as_primary_key(self):
        """TicketEvent has id column as Integer primary key."""
        mapper = TicketEvent.__mapper__
        id_column = mapper.columns.get("id")
        assert id_column is not None
        assert id_column.primary_key

    def test_ticket_event_has_ticket_id_as_foreign_key(self):
        """TicketEvent has ticket_id as Integer ForeignKey to tickets.id."""
        mapper = TicketEvent.__mapper__
        ticket_id_column = mapper.columns.get("ticket_id")
        assert ticket_id_column is not None
        # Check that it's a foreign key to tickets.id
        assert len(ticket_id_column.foreign_keys) == 1
        fk = list(ticket_id_column.foreign_keys)[0]
        assert fk.column.table.name == "tickets"
        assert fk.column.name == "id"

    def test_ticket_event_has_actor_column(self):
        """TicketEvent has actor column as String."""
        mapper = TicketEvent.__mapper__
        actor_column = mapper.columns.get("actor")
        assert actor_column is not None

    def test_ticket_event_has_kind_column(self):
        """TicketEvent has kind column as String."""
        mapper = TicketEvent.__mapper__
        kind_column = mapper.columns.get("kind")
        assert kind_column is not None

    def test_ticket_event_has_from_status_column_nullable(self):
        """TicketEvent has from_status column as String, nullable."""
        mapper = TicketEvent.__mapper__
        from_status_column = mapper.columns.get("from_status")
        assert from_status_column is not None
        assert from_status_column.nullable is True

    def test_ticket_event_has_to_status_column_nullable(self):
        """TicketEvent has to_status column as String, nullable."""
        mapper = TicketEvent.__mapper__
        to_status_column = mapper.columns.get("to_status")
        assert to_status_column is not None
        assert to_status_column.nullable is True

    def test_ticket_event_has_at_column_with_timezone(self):
        """TicketEvent has at column as DateTime(timezone=True)."""
        mapper = TicketEvent.__mapper__
        at_column = mapper.columns.get("at")
        assert at_column is not None
        assert hasattr(at_column.type, "timezone")
        assert at_column.type.timezone is True

    def test_ticket_event_has_exactly_the_required_columns(self):
        """TicketEvent has exactly id, ticket_id, actor, kind, from_status, to_status, at."""
        mapper = TicketEvent.__mapper__
        column_names = {col.name for col in mapper.columns}
        expected = {"id", "ticket_id", "actor", "kind", "from_status", "to_status", "at"}
        assert column_names == expected


class TestInitDbCreatesTables:
    """Tests that init_db() creates the comments and ticket_events tables."""

    def test_init_db_creates_comments_table(self, tables):
        """init_db() creates the comments table."""
        from app.db import init_db
        # Tables are dropped by the fixture; init_db must create them
        init_db()
        # Get inspector to check existing tables
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        assert "comments" in table_names

    def test_init_db_creates_ticket_events_table(self, tables):
        """init_db() creates the ticket_events table."""
        from app.db import init_db
        # Tables are dropped by the fixture; init_db must create them
        init_db()
        # Get inspector to check existing tables
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        assert "ticket_events" in table_names

    def test_init_db_creates_tickets_table(self, tables):
        """init_db() creates the tickets table (unchanged)."""
        from app.db import init_db
        # Tables are dropped by the fixture; init_db must create them
        init_db()
        # Get inspector to check existing tables
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        assert "tickets" in table_names

    def test_ticket_model_unchanged(self):
        """Ticket model is unchanged - has all original columns."""
        mapper = Ticket.__mapper__
        column_names = {col.name for col in mapper.columns}
        expected = {
            "id", "title", "details", "priority", "due",
            "status", "filed_by", "assigned_to", "created_at", "updated_at"
        }
        assert column_names == expected
