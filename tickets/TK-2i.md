id: TK-2i
unit: TK-2
state: in review
depends_on: TK-2f
done_when: backend/app/main.py adds GET /api/me, which answers 200 with {"user": "her"} for the TOKEN_HER token and {"user": "him"} for the TOKEN_HIM token; GET /api/me without the Authorization header, or with a token matching neither user, answers 401 with {"error": "unauthorized"}

# TK-2i
