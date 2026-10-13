import os
import sys
import importlib
from unittest.mock import patch

import pytest
from sqlalchemy import inspect


class TestDbModule:
    """Tests for backend/app/db.py environment variable handling and exports."""

    def test_db_raises_when_url_unset(self, monkeypatch):
        """Clause 1: RuntimeError when TICKETER_DATABASE_URL is unset."""
        # Remove the variable if it exists
        monkeypatch.delenv("TICKETER_DATABASE_URL", raising=False)

        # Remove any cached import of app.db so we can test fresh import
        modules_to_remove = [k for k in sys.modules if k.startswith("app")]
        for mod in modules_to_remove:
            del sys.modules[mod]

        with pytest.raises(RuntimeError, match="TICKETER_DATABASE_URL"):
            # Importing the module should raise at import time
            import app.db  # noqa: F401

    def test_db_raises_when_url_empty(self, monkeypatch):
        """Clause 1: RuntimeError when TICKETER_DATABASE_URL is empty."""
        monkeypatch.setenv("TICKETER_DATABASE_URL", "")

        # Remove any cached import of app.db so we can test fresh import
        modules_to_remove = [k for k in sys.modules if k.startswith("app")]
        for mod in modules_to_remove:
            del sys.modules[mod]

        with pytest.raises(RuntimeError, match="TICKETER_DATABASE_URL"):
            # Importing the module should raise at import time
            import app.db  # noqa: F401

    def test_db_exports_engine(self, monkeypatch):
        """Clause 2: db.py defines engine."""
        # Set a valid URL for this test (SQLite in-memory is fine for checking exports)
        monkeypatch.setenv("TICKETER_DATABASE_URL", "sqlite:///:memory:")

        import app.db as db_module

        importlib.reload(db_module)

        assert hasattr(db_module, "engine")
        assert db_module.engine is not None

    def test_db_exports_base(self, monkeypatch):
        """Clause 2: db.py defines Base."""
        monkeypatch.setenv("TICKETER_DATABASE_URL", "sqlite:///:memory:")

        import app.db as db_module

        importlib.reload(db_module)

        assert hasattr(db_module, "Base")
        assert db_module.Base is not None

    def test_db_exports_sessionlocal(self, monkeypatch):
        """Clause 2: db.py defines SessionLocal."""
        monkeypatch.setenv("TICKETER_DATABASE_URL", "sqlite:///:memory:")

        import app.db as db_module

        importlib.reload(db_module)

        assert hasattr(db_module, "SessionLocal")
        assert db_module.SessionLocal is not None

    def test_db_exports_init_db(self, monkeypatch):
        """Clause 2: db.py defines init_db()."""
        monkeypatch.setenv("TICKETER_DATABASE_URL", "sqlite:///:memory:")

        import app.db as db_module

        importlib.reload(db_module)

        assert hasattr(db_module, "init_db")
        assert callable(db_module.init_db)

    def test_base_is_declarative_subclass(self, monkeypatch):
        """Clause 2: Base is a subclass of sqlalchemy.orm.DeclarativeBase."""
        monkeypatch.setenv("TICKETER_DATABASE_URL", "sqlite:///:memory:")

        import app.db as db_module
        from sqlalchemy.orm import DeclarativeBase

        importlib.reload(db_module)

        assert issubclass(db_module.Base, DeclarativeBase)

    def test_init_db_creates_tables(self, monkeypatch):
        """Clause 2: init_db() imports app.models and creates every table."""
        monkeypatch.setenv("TICKETER_DATABASE_URL", "sqlite:///:memory:")

        import app.db as db_module

        importlib.reload(db_module)

        # Call init_db to create tables
        db_module.init_db()

        # Verify tables exist by inspecting the engine
        inspector = inspect(db_module.engine)
        table_names = inspector.get_table_names()

        assert "tickets" in table_names


class TestTicketModel:
    """Tests for backend/app/models.py Ticket model definition."""

    def test_ticket_model_exists(self, monkeypatch):
        """Clause 3: models.py defines the model Ticket."""
        monkeypatch.setenv("TICKETER_DATABASE_URL", "sqlite:///:memory:")

        import app.models as models_module

        assert hasattr(models_module, "Ticket")
        assert models_module.Ticket is not None

    def test_ticket_table_name(self, monkeypatch):
        """Clause 3: Ticket has table name 'tickets'."""
        monkeypatch.setenv("TICKETER_DATABASE_URL", "sqlite:///:memory:")

        import app.db as db_module
        import app.models as models_module

        importlib.reload(db_module)
        importlib.reload(models_module)

        assert models_module.Ticket.__tablename__ == "tickets"

    def test_ticket_has_id_column(self, monkeypatch):
        """Clause 3: Ticket has id column (Integer primary key)."""
        monkeypatch.setenv("TICKETER_DATABASE_URL", "sqlite:///:memory:")

        import app.models as models_module

        # Check that the model has an id attribute
        assert hasattr(models_module.Ticket, "id")

    def test_ticket_has_title_column(self, monkeypatch):
        """Clause 3: Ticket has title column (String(120))."""
        monkeypatch.setenv("TICKETER_DATABASE_URL", "sqlite:///:memory:")

        import app.models as models_module

        assert hasattr(models_module.Ticket, "title")

    def test_ticket_has_details_column(self, monkeypatch):
        """Clause 3: Ticket has details column (String(1000), default '')."""
        monkeypatch.setenv("TICKETER_DATABASE_URL", "sqlite:///:memory:")

        import app.models as models_module

        assert hasattr(models_module.Ticket, "details")

    def test_ticket_has_priority_column(self, monkeypatch):
        """Clause 3: Ticket has priority column (String)."""
        monkeypatch.setenv("TICKETER_DATABASE_URL", "sqlite:///:memory:")

        import app.models as models_module

        assert hasattr(models_module.Ticket, "priority")

    def test_ticket_has_due_column(self, monkeypatch):
        """Clause 3: Ticket has due column (Date, nullable)."""
        monkeypatch.setenv("TICKETER_DATABASE_URL", "sqlite:///:memory:")

        import app.models as models_module

        assert hasattr(models_module.Ticket, "due")

    def test_ticket_has_status_column(self, monkeypatch):
        """Clause 3: Ticket has status column (String)."""
        monkeypatch.setenv("TICKETER_DATABASE_URL", "sqlite:///:memory:")

        import app.models as models_module

        assert hasattr(models_module.Ticket, "status")

    def test_ticket_has_filed_by_column(self, monkeypatch):
        """Clause 3: Ticket has filed_by column (String)."""
        monkeypatch.setenv("TICKETER_DATABASE_URL", "sqlite:///:memory:")

        import app.models as models_module

        assert hasattr(models_module.Ticket, "filed_by")

    def test_ticket_has_assigned_to_column(self, monkeypatch):
        """Clause 3: Ticket has assigned_to column (String)."""
        monkeypatch.setenv("TICKETER_DATABASE_URL", "sqlite:///:memory:")

        import app.models as models_module

        assert hasattr(models_module.Ticket, "assigned_to")

    def test_ticket_has_created_at_column(self, monkeypatch):
        """Clause 3: Ticket has created_at column (DateTime(timezone=True))."""
        monkeypatch.setenv("TICKETER_DATABASE_URL", "sqlite:///:memory:")

        import app.models as models_module

        assert hasattr(models_module.Ticket, "created_at")

    def test_ticket_has_updated_at_column(self, monkeypatch):
        """Clause 3: Ticket has updated_at column (DateTime(timezone=True))."""
        monkeypatch.setenv("TICKETER_DATABASE_URL", "sqlite:///:memory:")

        import app.models as models_module

        assert hasattr(models_module.Ticket, "updated_at")

    def test_ticket_has_exactly_required_columns(self, monkeypatch):
        """Clause 3: Ticket has exactly the specified columns."""
        monkeypatch.setenv("TICKETER_DATABASE_URL", "sqlite:///:memory:")

        import app.models as models_module

        required_columns = {
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

        # Get all column names from the model's __table__
        actual_columns = {col.name for col in models_module.Ticket.__table__.columns}

        assert actual_columns == required_columns
