import unittest
import os
from fastapi.testclient import TestClient
import pytest

try:
    from app.main import app
except ImportError:
    app = None

class TestTicketerAPI(unittest.TestCase):
    def setUp(self):
        if app is None:
            self.fail("app.main.app not found")
        self.client = TestClient(app)
        os.environ["TOKEN_HER"] = "secret_her"
        os.environ["TOKEN_HIM"] = "secret_him"
        os.environ["TICKETER_DATABASE_URL"] = "postgresql://user:pass@localhost/test_db"

    def test_health_endpoint(self):
        # Clause 7: GET /health answers 200 with {"status": "ok"} and needs no credential
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        # Assert it doesn't refuse (no 401/403)
        self.assertNotIn(response.status_code, (401, 403))

    def test_health_endpoint_with_invalid_token(self):
        # Clause 7: GET /health needs no credential (should not be blocked by wrong token)
        response = self.client.get("/health", headers={"Authorization": "Bearer wrong"})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(response.status_code, (401, 403))

    def test_unauthorized_access(self):
        # Clause 2: Missing header, wrong token, or empty env var -> 401
        response = self.client.get("/api/filed")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"error": "unauthorized"})

        response = self.client.get("/api/filed", headers={"Authorization": "Bearer wrong"})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"error": "unauthorized"})

    def test_authentication_success(self):
        # Clause 2: Valid tokens identify caller
        response = self.client.get("/api/filed", headers={"Authorization": "Bearer secret_her"})
        self.assertNotEqual(response.status_code, 401)

    def test_create_ticket_api(self):
        # Clause 3: POST /api/tickets creates ticket and answers 201
        payload = {"title": "Test Ticket", "priority": "normal"}
        headers = {"Authorization": "Bearer secret_her"}
        response = self.client.post("/api/tickets", json=payload, headers=headers)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["title"], "Test Ticket")

    def test_change_status_api_not_found(self):
        # Clause 4: POST /api/tickets/{id}/status -> 404 on LookupError
        headers = {"Authorization": "Bearer secret_him"}
        response = self.client.post("/api/tickets/999/status", json={"status": "acknowledged"}, headers=headers)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"error": "not found"})

    def test_other_user_cannot_make_the_assignees_move(self):
        # Clause 4: POST /api/tickets/{id}/status -> 403 on PermissionError
        # Setup: Her files a ticket, Him is assignee. Her tries to acknowledge it.
        headers_her = {"Authorization": "Bearer secret_her"}
        headers_him = {"Authorization": "Bearer secret_him"}
        
        # Create ticket
        create_res = self.client.post("/api/tickets", json={"title": "Authz Test"}, headers=headers_her)
        ticket_id = create_res.json()["id"]
        
        # Filer (her) tries to move to acknowledged (assignee move)
        response = self.client.post(f"/api/tickets/{ticket_id}/status", json={"status": "acknowledged"}, headers=headers_her)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json(), {"error": "forbidden"})
        
        # Verify status is still open
        # We use dashboard or filed to check status since there is no GET /api/tickets/{id}
        dash_res = self.client.get("/api/dashboard", headers=headers_him)
        todo = dash_res.json()["todo"]
        ticket = next(t for t in todo if t["id"] == ticket_id)
        self.assertEqual(ticket["status"], "open")

    def test_dashboard_api(self):
        # Clause 5: GET /api/dashboard
        headers = {"Authorization": "Bearer secret_her"}
        response = self.client.get("/api/dashboard", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertIn("todo", response.json())

    def test_filed_api(self):
        # Clause 6: GET /api/filed
        headers = {"Authorization": "Bearer secret_her"}
        response = self.client.get("/api/filed", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertIn("tickets", response.json())

    def test_invalid_request_handling(self):
        # Clause 8: Malformed JSON or invalid fields -> 400
        headers = {"Authorization": "Bearer secret_her"}
        response = self.client.post("/api/tickets", json=[1, 2, 3], headers=headers)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "invalid request"})
        
        response = self.client.post("/api/tickets/abc/status", json={"status": "done"}, headers=headers)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "invalid request"})

    def test_body_size_limit(self):
        # Clause 9: Body > 64KiB -> 413
        headers = {"Authorization": "Bearer secret_her"}
        large_body = "a" * 65537
        response = self.client.post("/api/tickets", content=large_body, headers=headers)
        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.json(), {"error": "too large"})

    def test_unknown_path_and_method(self):
        # Clause 10: 404 unknown path, 405 wrong method
        response = self.client.get("/api/does-not-exist")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"error": "not found"})

        response = self.client.put("/health")
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.json(), {"error": "method not allowed"})

    def test_security_headers(self):
        # Clause 11: Security headers on every response
        response = self.client.get("/health")
        self.assertEqual(response.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(response.headers.get("Content-Security-Policy"), "default-src 'none'")
        self.assertEqual(response.headers.get("Cache-Control"), "no-store")
        self.assertEqual(response.headers.get("Referrer-Policy"), "no-referrer")
