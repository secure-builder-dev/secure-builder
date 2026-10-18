import os
import hmac
import datetime
from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.responses import JSONResponse
from starlette import status

# Import the app's internal modules
from app import db as db_mod
from app import rules

app = FastAPI()

# ---------------------------------------------------------------------------
# Lifespan / startup
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def startup_event() -> None:
    """Initialize the database when the application starts.

    The ``init_db`` function creates all tables defined in ``app.models``.
    """
    db_mod.init_db()

# ---------------------------------------------------------------------------
# Security / authentication helper
# ---------------------------------------------------------------------------
def get_caller(request: Request) -> str:
    """Extract the caller identity from the ``Authorization`` header.

    The header must be exactly ``Bearer <token>``. The token is compared
    against the environment variables ``TOKEN_HER`` and ``TOKEN_HIM`` using
    ``hmac.compare_digest``.  If the token matches ``TOKEN_HER`` the caller
    is ``"her"``; if it matches ``TOKEN_HIM`` the caller is ``"him"``.
    Any mismatch, missing header, wrong scheme, empty token, or an unset or
    empty environment variable results in a ``401`` response with the JSON
    body ``{"error": "unauthorized"}``.
    """
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")
    token = auth[7:]  # strip "Bearer "

    # Retrieve tokens from the environment; treat missing/empty as non‑matching
    token_her = os.getenv("TOKEN_HER") or ""
    token_him = os.getenv("TOKEN_HIM") or ""

    if token and token_her and hmac.compare_digest(token, token_her):
        return "her"
    if token and token_him and hmac.compare_digest(token, token_him):
        return "him"
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")

# ---------------------------------------------------------------------------
# Database session dependency (one per request)
# ---------------------------------------------------------------------------
def get_db():
    """Yield a SQLAlchemy session and ensure it is closed after the request."""
    db = db_mod.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/health")
async def health() -> dict:
    """Public health check – no authentication required."""
    return {"status": "ok"}

@app.get("/api/dashboard")
async def api_dashboard(
    caller: str = Depends(get_caller),
    session=Depends(get_db),
) -> dict:
    """Return the personal board for the authenticated caller.

    ``today`` is the current UTC date.
    """
    today = datetime.datetime.now(datetime.timezone.utc).date()
    return rules.dashboard(session, caller, today)

@app.get("/api/filed")
async def api_filed(
    caller: str = Depends(get_caller),
    session=Depends(get_db),
) -> dict:
    """Return the tickets filed by the authenticated caller."""
    return {"tickets": rules.filed(session, caller)}

# ---------------------------------------------------------------------------
# Error handling – always JSON with a lower‑case ``error`` field
# ---------------------------------------------------------------------------
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    # Normalise the detail to lower‑case as required by the tests
    detail = exc.detail
    if isinstance(detail, str):
        detail = detail.lower()
    else:
        # Fallback for non‑string details
        detail = str(detail).lower()
    return JSONResponse(status_code=exc.status_code, content={"error": detail})

# Explicit handlers for 404 and 405 to ensure JSON shape matches tests
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(status_code=404, content={"error": "not found"})

@app.exception_handler(405)
async def method_not_allowed_handler(request: Request, exc):
    return JSONResponse(status_code=405, content={"error": "method not allowed"})

# ---------------------------------------------------------------------------
# Middleware – add the required security headers to every response
# ---------------------------------------------------------------------------
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = "default-src 'none'"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response
