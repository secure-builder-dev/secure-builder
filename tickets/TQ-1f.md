id: TQ-1f
unit: TQ-1
state: in review
depends_on: TQ-1e
done_when: backend/app/main.py defines the FastAPI application app, whose startup (a lifespan handler) calls db.init_db(), and which opens one database session per request (a dependency that closes it after the request); get_caller(request) reads the header Authorization: Bearer <token> and returns 'her' when the token equals the environment variable TOKEN_HER and 'him' when it equals TOKEN_HIM, comparing with hmac.compare_digest and reading the variables on every request — a missing header, another scheme, an empty token, a token matching neither, or an unset or empty variable is answered 401 with {"error": "unauthorized"}; GET /health answers 200 with {"status": "ok"} and needs no credential; GET /api/dashboard answers 200 with rules.dashboard(session, caller, today) where today is the current UTC date (datetime.now(timezone.utc).date()), and GET /api/filed answers 200 with {"tickets": rules.filed(session, caller)}; an unknown path answers 404 with {"error": "not found"} and a wrong method 405 with {"error": "method not allowed"} (an exception handler for starlette's HTTPException); every response, errors included, carries the headers X-Content-Type-Options: nosniff, Content-Security-Policy: default-src 'none', Cache-Control: no-store and Referrer-Policy: no-referrer (one HTTP middleware)

# TQ-1f
