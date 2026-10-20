import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


_url = os.environ.get("TICKETER_DATABASE_URL")
if not _url:
    raise RuntimeError("TICKETER_DATABASE_URL is not set")

engine = create_engine(_url)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_db():
    import app.models  # noqa: F401
    Base.metadata.create_all(engine)
