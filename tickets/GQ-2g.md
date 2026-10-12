id: GQ-2g
unit: GQ-2
state: claimed
depends_on: GQ-2d
done_when: backend/app/main.py adds GET /api/me, which needs the caller (401 {"error": "unauthorized"} without a valid token) and answers 200 with {"user": caller}; every other route keeps its behaviour

# GQ-2g
