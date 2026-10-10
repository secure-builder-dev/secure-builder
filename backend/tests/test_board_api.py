import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db import SessionLocal, init_db, Base, engine
from app.models import Ticket
import os
from datetime import datetime, timezone, date, timedelta

@pytest.fixture(autouse=True)
def setup_db():
    # Create tables before each test
    init_db()
    yield
    # Drop tables after each test
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client():
    return TestClient(app)

def test_get_board_success_her(client, monkeypatch):
    monkeypatch.setenv('TOKEN_HER', 'secret_her')
    monkeypatch.setenv('TOKEN_HIM', 'secret_him')
    
    # Create a ticket to ensure board is not empty
    with SessionLocal() as session:
        t = Ticket(title="Test", status="open", filed_by="him", assigned_to="her", 
                   created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))
        session.add(t)
        session.commit()

    response = client.get('/api/board', headers={'Authorization': 'Bearer secret_her'})
    assert response.status_code == 200
    data = response.json()
    assert 'todo' in data
    assert 'in_progress' in data
    assert 'completed' in data
    assert len(data['todo']) == 1

def test_get_board_consistency_her_him(client, monkeypatch):
    monkeypatch.setenv('TOKEN_HER', 'secret_her')
    monkeypatch.setenv('TOKEN_HIM', 'secret_him')
    
    with SessionLocal() as session:
        t = Ticket(title="Shared", status="open", filed_by="her", assigned_to="him", 
                   created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))
        session.add(t)
        session.commit()
    
    res_her = client.get('/api/board', headers={'Authorization': 'Bearer secret_her'})
    res_him = client.get('/api/board', headers={'Authorization': 'Bearer secret_him'})
    
    assert res_her.status_code == 200
    assert res_him.status_code == 200
    assert res_her.json() == res_him.json()

def test_get_board_unauthorized_no_header(client, monkeypatch):
    monkeypatch.setenv('TOKEN_HER', 'secret_her')
    monkeypatch.setenv('TOKEN_HIM', 'secret_him')
    
    response = client.get('/api/board')
    assert response.status_code == 401
    assert response.json() == {'error': 'unauthorized'}

def test_get_board_unauthorized_wrong_token(client, monkeypatch):
    monkeypatch.setenv('TOKEN_HER', 'secret_her')
    monkeypatch.setenv('TOKEN_HIM', 'secret_him')
    
    response = client.get('/api/board', headers={'Authorization': 'Bearer wrong_token'})
    assert response.status_code == 401
    assert response.json() == {'error': 'unauthorized'}

def test_get_board_completed_window(client, monkeypatch):
    monkeypatch.setenv('TOKEN_HER', 'secret_her')
    monkeypatch.setenv('TOKEN_HIM', 'secret_him')
    
    today = datetime.now(timezone.utc)
    with SessionLocal() as session:
        # Within 7 days
        t1 = Ticket(title="Recent", status="done", filed_by="her", assigned_to="him", 
                    created_at=today - timedelta(days=2), updated_at=today - timedelta(days=1))
        # Older than 7 days
        t2 = Ticket(title="Old", status="done", filed_by="her", assigned_to="him", 
                    created_at=today - timedelta(days=10), updated_at=today - timedelta(days=8))
        session.add_all([t1, t2])
        session.commit()
    
    response = client.get('/api/board', headers={'Authorization': 'Bearer secret_her'})
    data = response.json()
    assert len(data['completed']) == 1
    assert data['completed'][0]['title'] == "Recent"