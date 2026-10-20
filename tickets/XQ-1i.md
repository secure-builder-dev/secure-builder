id: XQ-1i
unit: XQ-1
state: in review
depends_on: XQ-1h
done_when: backend/app/main.py adds GET /api/me, which needs the caller (401 {"error": "unauthorized"} without a valid token) and answers 200 with {"user": caller}; every other route keeps its behaviour

# XQ-1i
