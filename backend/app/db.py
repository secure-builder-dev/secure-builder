from sqlalchemy import create_engine
import os
database_url = os.getenv('TICKETER_DATABASE_URL')
if not database_url:
    raise RuntimeError('TICKETER_DATABASE_URL must be set')
engine = create_engine(database_url)

from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)