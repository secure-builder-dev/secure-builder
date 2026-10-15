"""Unit tests for models (given by the plan; read-only)."""
import subprocess
import sys

import pytest
from sqlalchemy import inspect


class TestDbModule:
    """Clauses 1 and 2: db.py reads TICKETER_DATABASE_URL and defines engine, Base, SessionLocal, init_db."""

    def test_unset_env_raises_runtime_error(self):
        """Clause 1: unset TICKETER_DATABASE_URL raises RuntimeError."""
        env = {k: v for k, v in dict(**sys.modules["os"].environ).items() if k != "TICKETER_DATABASE_URL"}
        result = subprocess.run(
            [sys.executable, "-c", "import app.db"],
            cwd=sys.modules["app.db"].__file__.replace("db.py", ""),
            env=env,
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "RuntimeError" in result.stderr

    def test_empty_env_raises_runtime_error(self):
        """Clause 1: empty TICKETER_DATABASE_URL raises RuntimeError."""
        env = {**sys.modules["os"].environ, "TICKETER_DATABASE_URL": ""}
        result = subprocess.run(
            [sys.executable, "-c", "import app.db"],
            cwd=sys.modules["app.db"].__file__.replace("db.py", ""),
            env=env,
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "RuntimeError" in result.stderr

    def test_exports_exist(self):
        """Clause 2: engine, Base, SessionLocal, init_db are exported."""
        from app.db import Base, SessionLocal, engine, init_db

        assert engine is not None
        assert isinstance(Base, type) and issubclass(Base, inspect(Base).mapper.class_)
        assert SessionLocal is not None
        assert callable(init_db)


class TestTicketModel:
    """Clause 3: Ticket model has table name tickets and exact columns."""

    def test_table_name_and_columns(self, db):
        """Clause 3: Ticket.__table__.name is 'tickets' and columns match exactly."""
        from app.models import Ticket

        table = Ticket.__table__
        assert table.name == "tickets"
        columns = {c.name: c for c in table.columns}
        assert columns["id"].type.python_type == int
        assert columns["title"].type.length == 120
        assert columns["details"].type.length == 1000
        assert columns["details"].default.value == ""
        assert columns["priority"].type.python_type == str
        assert columns["due"].type.python_type == str
        assert columns["due"].nullable is True
        assert columns["status"].type.python_type == str
        assert columns["filed_by"].type.python_type == str
        assert columns["assigned_to"].type.python_type == str
        assert columns["created_at"].type.python_type == str
        assert columns["updated_at"].type.python_type == str