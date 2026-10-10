import os
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_tokens(monkeypatch):
    monkeypatch.setenv('TOKEN_HER', 'secret_her')
    monkeypatch.setenv('TOKEN_HIM', 'secret_him')

def test_get_me_her():
    response = client.get('/api/me', headers={'Authorization': 'Bearer secret_her'})
    assert response.status_code == 200
    assert response.json() == {'user': 'her'}

def test_get_me_him():
    response = client.get('/api/me', headers={'Authorization': 'Bearer secret_him'})
    assert response.status_code == 200
    assert response.json() == {'user': 'him'}

def test_get_me_no_auth():
    response = client.get('/api/me')
    assert response.status_code == 401
    assert response.json() == {'error': 'unauthorized'}

def test_get_me_wrong_token():
    response = client.get('/api/me', headers={'Authorization': 'Bearer wrong_token'})
    assert response.status_code == 401
    assert response.json() == {'error': 'unauthorized'}