id: GV-2d
unit: GV-2
state: claimed
depends_on: GV-2c
done_when: backend/app/main.py adds GET /api/board, which needs the caller (401 {"error": "unauthorized"} without a valid token) and answers 200 with household.household_board(session, today), today being the current UTC date, so both users get the same board; every other route keeps its behaviour

# GV-2d
