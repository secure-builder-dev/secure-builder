id: GQ-2d
unit: GQ-2
state: in review
depends_on: GQ-2c
done_when: backend/app/main.py adds GET /api/board, which needs the caller (401 {"error": "unauthorized"} without a valid token) and answers 200 with household.household_board(session, today), today being the current UTC date, so both users get the same board; every other route keeps its behaviour

# GQ-2d
