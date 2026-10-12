id: GV-2g
unit: GV-2
state: claimed
depends_on: GV-2d
done_when: backend/app/main.py adds GET /api/me, which needs the caller (401 {"error": "unauthorized"} without a valid token) and answers 200 with {"user": caller}; every other route keeps its behaviour

# GV-2g
