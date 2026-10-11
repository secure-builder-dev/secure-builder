id: FD-2i
unit: FD-2
state: in review
depends_on: FD-2f
done_when: backend/app/main.py adds GET /api/me, which answers 200 with {"user": "her"} for the TOKEN_HER token and {"user": "him"} for the TOKEN_HIM token; GET /api/me without the Authorization header, or with a token matching neither user, answers 401 with {"error": "unauthorized"}; every test in backend/tests/test_api.py and backend/tests/test_board_api.py still passes; every clause has a pytest test in backend/tests/test_me_api.py that uses the database in TICKETER_DATABASE_URL with the tables created before each test and dropped after, uses fastapi.testclient.TestClient and sets TOKEN_HER and TOKEN_HIM with monkeypatch.setenv

# FD-2i
