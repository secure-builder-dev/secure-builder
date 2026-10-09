from sqlalchemy import create_engine
import os
default_database_url = 'postgresql+psycopg://postgres@127.0.0.1:55432/ticketer'
database_url = os.getenv('TICKETER_DATABASE_URL', default_database_url)
engine = create_engine(database_url)

from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)