id: TQ-1h
unit: TQ-1
state: in review
depends_on: TQ-1g
done_when: backend/app/main.py adds GET /api/board, which needs the caller (401 {"error": "unauthorized"} without a valid token) and answers 200 with household.household_board(session, today), today being the current UTC date, so both users get the same board; every other route keeps its behaviour

# TQ-1h
