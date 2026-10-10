import pytest
from datetime import datetime, date, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

from app.db import Base
from app.models import Ticket
from app.rules import create_ticket

# The function we are testing is expected to be in app.household
try:
    from app.household import household_board
except ImportError:
    household_board = None

DATABASE_URL = os.getenv('TICKETER_DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/ticketer_test')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)

def test_household_board_exists_and_returns_structure(setup_db):
    """Clause 1: household_board exists, takes date, returns correct structure with all users' tickets"""
    session = setup_db
    today = date(2026, 1, 10)
    
    # Create tickets for both users
    create_ticket(session, 'her', {'title': 'T1'})
    create_ticket(session, 'him', {'title': 'T2'})
    
    if household_board is None:
        pytest.fail("app.household.household_board is not defined")
    
    result = household_board(session, today)
    assert isinstance(result, dict)
    assert set(result.keys()) == {'todo', 'in_progress', 'completed'}
    # Both tickets should be in todo by default
    assert len(result['todo']) == 2

def test_household_board_todo_in_progress_ordering(setup_db):
    """Clause 2: todo (open/acknowledged) and in_progress (in_progress) ordered by oldest created_at first"""
    session = setup_db
    today = date(2026, 1, 10)
    
    # T1: Oldest, open
    t1 = Ticket(title='T1', filed_by='her', assigned_to='him', status='open', 
                created_at=datetime(2026, 1, 1, tzinfo=timezone.utc), updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    # T2: Newer, acknowledged
    t2 = Ticket(title='T2', filed_by='him', assigned_to='her', status='acknowledged', 
                created_at=datetime(2026, 1, 2, tzinfo=timezone.utc), updated_at=datetime(2026, 1, 2, tzinfo=timezone.utc))
    # T3: Oldest, in_progress
    t3 = Ticket(title='T3', filed_by='her', assigned_to='him', status='in_progress', 
                created_at=datetime(2026, 1, 1, tzinfo=timezone.utc), updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    # T4: Newer, in_progress
    t4 = Ticket(title='T4', filed_by='him', assigned_to='her', status='in_progress', 
                created_at=datetime(2026, 1, 2, tzinfo=timezone.utc), updated_at=datetime(2026, 1, 2, tzinfo=timezone.utc))
    
    session.add_all([t1, t2, t3, t4])
    session.commit()
    
    if household_board is None:
        pytest.fail("app.household.household_board is not defined")
    
    result = household_board(session, today)
    
    # Todo: T1 then T2
    assert [t['title'] for t in result['todo']] == ['T1', 'T2']
    # In Progress: T3 then T4
    assert [t['title'] for t in result['in_progress']] == ['T3', 'T4']

def test_household_board_completed_filtering_and_ordering(setup_db):
    """Clause 3: completed (done/closed) within 7 days ending today, newest updated_at first"""
    session = setup_db
    today = date(2026, 1, 10)
    
    # T1: Done, updated 2 days ago (In)
    t1 = Ticket(title='T1', filed_by='her', assigned_to='him', status='done', 
                created_at=datetime(2026, 1, 1, tzinfo=timezone.utc), 
                updated_at=datetime(2026, 1, 8, tzinfo=timezone.utc))
    # T2: Closed, updated 6 days ago (In)
    t2 = Ticket(title='T2', filed_by='him', assigned_to='her', status='closed', 
                created_at=datetime(2026, 1, 1, tzinfo=timezone.utc), 
                updated_at=datetime(2026, 1, 4, tzinfo=timezone.utc))
    # T3: Done, updated 8 days ago (Out)
    t3 = Ticket(title='T3', filed_by='her', assigned_to='him', status='done', 
                created_at=datetime(2026, 1, 1, tzinfo=timezone.utc), 
                updated_at=datetime(2026, 1, 2, tzinfo=timezone.utc))
    
    session.add_all([t1, t2, t3])
    session.commit()
    
    if household_board is None:
        pytest.fail("app.household.household_board is not defined")
    
    result = household_board(session, today)
    
    # Should contain T1 and T2, but not T3. Order: T1 (newest) then T2
    assert [t['title'] for t in result['completed']] == ['T1', 'T2']

def test_household_board_database_isolation(setup_db):
    """Clause 4: Verify database usage and isolation (tables created/dropped per test)
    This test specifically checks that we can set timestamps directly on the model
    and that the board reflects these database-level changes.
    """
    session = setup_db
    today = date(2026, 1, 10)
    
    # Directly insert a ticket with a specific timestamp
    t = Ticket(
        title='DB Test',
        filed_by='her',
        assigned_to='him',
        status='done',
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 9, tzinfo=timezone.utc)
    )
    session.add(t)
    session.commit()
    
    if household_board is None:
        pytest.fail("app.household.household_board is not defined")
    
    result = household_board(session, today)
    assert len(result['completed']) == 1
    assert result['completed'][0]['title'] == 'DB Test'