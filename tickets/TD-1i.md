id: TD-1i
unit: TD-1
state: open
depends_on: TD-1h
done_when: backend/app/main.py adds GET /api/me, which needs the caller (401 {"error": "unauthorized"} without a valid token) and answers 200 with {"user": caller}; every other route keeps its behaviour

# TD-1i
