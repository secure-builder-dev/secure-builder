id: XO-1i
unit: XO-1
state: in review
depends_on: XO-1h
done_when: backend/app/main.py adds GET /api/me, which needs the caller (401 {"error": "unauthorized"} without a valid token) and answers 200 with {"user": caller}; every other route keeps its behaviour

# XO-1i
