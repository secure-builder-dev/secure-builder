import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


def _get_database_url() -> str:
    url = os.environ.get("TICKETER_DATABASE_URL", "")
    if not url:
        raise RuntimeError("TICKETER_DATABASE_URL is unset or empty")
    return url


engine = create_engine(_get_database_url())
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    import app.models  # noqa: F401
    Base.metadata.create_all(engine)