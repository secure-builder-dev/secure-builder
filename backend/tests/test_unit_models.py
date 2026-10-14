import os
import subprocess
import sys
from unittest.mock import patch

import pytest
from sqlalchemy import inspect
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class TestDbModule:
    """Tests for backend/app/db.py environment variable handling and exports."""

    def test_db_raises_runtime_error_when_database_url_unset(self):
        """Clause 1: RuntimeError when TICKETER_DATABASE_URL is unset."""
        env = os.environ.copy()
        env.pop("TICKETER_DATABASE_URL", None)
        # Use absolute path for cwd to avoid Windows subprocess issues
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        result = subprocess.run(
            [sys.executable, "-c", "import app.db"],
            cwd=backend_dir,
            env=env,
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "RuntimeError" in result.stderr or "TICKETER_DATABASE_URL" in result.stderr

    def test_db_raises_runtime_error_when_database_url_empty(self):
        """Clause 1: RuntimeError when TICKETER_DATABASE_URL is empty."""
        env = os.environ.copy()
        env["TICKETER_DATABASE_URL"] = ""
        # Use absolute path for cwd to avoid Windows subprocess issues
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        result = subprocess.run(
            [sys.executable, "-c", "import app.db"],
            cwd=backend_dir,
            env=env,
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "RuntimeError" in result.stderr or "TICKETER_DATABASE_URL" in result.stderr

    def test_db_exports_engine(self, monkeypatch):
        """Clause 2: db.py defines engine."""
        monkeypatch.setenv("TICKETER_DATABASE_URL", "postgresql://test:test@localhost/test")
        import app.db

        assert hasattr(app.db, "engine")
        assert app.db.engine is not None

    def test_db_exports_base_as_declarative_base_subclass(self, monkeypatch):
        """Clause 2: db.py defines Base as a subclass of DeclarativeBase."""
        monkeypatch.setenv("TICKETER_DATABASE_URL", "postgresql://test:test@localhost/test")
        import app.db

        assert hasattr(app.db, "Base")
        assert issubclass(app.db.Base, DeclarativeBase)

    def test_db_exports_sessionlocal_as_sessionmaker(self, monkeypatch):
        """Clause 2: db.py defines SessionLocal as a sessionmaker bound to engine."""
        monkeypatch.setenv("TICKETER_DATABASE_URL", "postgresql://test:test@localhost/test")
        import app.db

        assert hasattr(app.db, "SessionLocal")
        # SessionLocal should be callable and return a session-like object
        assert isinstance(app.db.SessionLocal, type(sessionmaker()))

    def test_db_exports_init_db_function(self, monkeypatch):
        """Clause 2: db.py defines init_db()."""
        monkeypatch.setenv("TICKETER_DATABASE_URL", "postgresql://test:test@localhost/test")
        import app.db

        assert hasattr(app.db, "init_db")
        assert callable(app.db.init_db)


class TestTicketModel:
    """Tests for backend/app/models.py Ticket model definition."""

    def test_ticket_model_exists(self, monkeypatch):
        """Clause 3: models.py defines the model Ticket."""
        monkeypatch.setenv("TICKETER_DATABASE_URL", "postgresql://test:test@localhost/test")
        import app.models

        assert hasattr(app.models, "Ticket")

    def test_ticket_has_correct_table_name(self, monkeypatch):
        """Clause 3: Ticket has table name 'tickets'."""
        monkeypatch.setenv("TICKETER_DATABASE_URL", "postgresql://test:test@localhost/test")
        import app.models

        assert app.models.Ticket.__tablename__ == "tickets"

    def test_ticket_has_id_column_as_integer_primary_key(self, monkeypatch):
        """Clause 3: Ticket has id column (Integer primary key)."""
        monkeypatch.setenv("TICKETER_DATABASE_URL", "postgresql://test:test@localhost/test")
        import app.models

        mapper = app.models.Ticket.__mapper__
        columns = {c.name: c for c in mapper.columns}
        assert "id" in columns
        assert columns["id"].primary_key

    def test_ticket_has_title_column_string_120(self, monkeypatch):
        """Clause 3: Ticket has title column (String(120))."""
        monkeypatch.setenv("TICKETER_DATABASE_URL", "postgresql://test:test@localhost/test")
        import app.models

        mapper = app.models.Ticket.__mapper__
        columns = {c.name: c for c in mapper.columns}
        assert "title" in columns
        # String(120) means length 120
        assert columns["title"].type.length == 120

    def test_ticket_has_details_column_string_1000_default_empty(self, monkeypatch):
        """Clause 3: Ticket has details column (String(1000), default '')."""
        monkeypatch.setenv("TICKETER_DATABASE_URL", "postgresql://test:test@localhost/test")
        import app.models

        mapper = app.models.Ticket.__mapper__
        columns = {c.name: c for c in mapper.columns}
        assert "details" in columns
        assert columns["details"].type.length == 1000
        # Check default value
        assert columns["details"].default is not None
        assert columns["details"].default.arg == ""

    def test_ticket_has_priority_column_string(self, monkeypatch):
        """Clause 3: Ticket has priority column (String)."""
        monkeypatch.setenv("TICKETER_DATABASE_URL", "postgresql://test:test@localhost/test")
        import app.models

        mapper = app.models.Ticket.__mapper__
        columns = {c.name: c for c in mapper.columns}
        assert "priority" in columns

    def test_ticket_has_due_column_date_nullable(self, monkeypatch):
        """Clause 3: Ticket has due column (Date, nullable)."""
        monkeypatch.setenv("TICKETER_DATABASE_URL", "postgresql://test:test@localhost/test")
        import app.models

        mapper = app.models.Ticket.__mapper__
        columns = {c.name: c for c in mapper.columns}
        assert "due" in columns
        assert columns["due"].nullable is True

    def test_ticket_has_status_column_string(self, monkeypatch):
        """Clause 3: Ticket has status column (String)."""
        monkeypatch.setenv("TICKETER_DATABASE_URL", "postgresql://test:test@localhost/test")
        import app.models

        mapper = app.models.Ticket.__mapper__
        columns = {c.name: c for c in mapper.columns}
        assert "status" in columns

    def test_ticket_has_filed_by_column_string(self, monkeypatch):
        """Clause 3: Ticket has filed_by column (String)."""
        monkeypatch.setenv("TICKETER_DATABASE_URL", "postgresql://test:test@localhost/test")
        import app.models

        mapper = app.models.Ticket.__mapper__
        columns = {c.name: c for c in mapper.columns}
        assert "filed_by" in columns

    def test_ticket_has_assigned_to_column_string(self, monkeypatch):
        """Clause 3: Ticket has assigned_to column (String)."""
        monkeypatch.setenv("TICKETER_DATABASE_URL", "postgresql://test:test@localhost/test")
        import app.models

        mapper = app.models.Ticket.__mapper__
        columns = {c.name: c for c in mapper.columns}
        assert "assigned_to" in columns

    def test_ticket_has_created_at_column_datetime_timezone(self, monkeypatch):
        """Clause 3: Ticket has created_at column (DateTime(timezone=True))."""
        monkeypatch.setenv("TICKETER_DATABASE_URL", "postgresql://test:test@localhost/test")
        import app.models

        mapper = app.models.Ticket.__mapper__
        columns = {c.name: c for c in mapper.columns}
        assert "created_at" in columns
        # Check that timezone is True
        assert columns["created_at"].type.timezone is True

    def test_ticket_has_updated_at_column_datetime_timezone(self, monkeypatch):
        """Clause 3: Ticket has updated_at column (DateTime(timezone=True))."""
        monkeypatch.setenv("TICKETER_DATABASE_URL", "postgresql://test:test@localhost/test")
        import app.models

        mapper = app.models.Ticket.__mapper__
        columns = {c.name: c for c in mapper.columns}
        assert "updated_at" in columns
        # Check that timezone is True
        assert columns["updated_at"].type.timezone is True

    def test_ticket_has_exactly_the_required_columns(self, monkeypatch):
        """Clause 3: Ticket has exactly the specified columns (no more, no less)."""
        monkeypatch.setenv("TICKETER_DATABASE_URL", "postgresql://test:test@localhost/test")
        import app.models

        mapper = app.models.Ticket.__mapper__
        column_names = {c.name for c in mapper.columns}
        expected_columns = {
            "id",
            "title",
            "details",
            "priority",
            "due",
            "status",
            "filed_by",
            "assigned_to",
            "created_at",
            "updated_at",
        }
        assert column_names == expected_columns
