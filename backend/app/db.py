import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.environ.get("TICKETER_DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("TICKETER_DATABASE_URL is unset or empty")

engine = create_engine(DATABASE_URL)
class Base(DeclarativeBase):
    pass
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    from app import models  # noqa: F401
    Base.metadata.create_all(bind=engine)