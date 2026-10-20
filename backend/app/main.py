import os
import hmac
from datetime import datetime, timezone
from typing import Generator

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import db, rules
from app.db import SessionLocal

app = FastAPI()

# ---------------------------------------------------------------------------
# Lifespan / startup
# ---------------------------------------------------------------------------
@app.on_event("startup")
def on_startup() -> None:
    """Initialize the database when the application starts.

    The test suite expects that ``db.init_db()`` is called during the
    application's startup (lifespan) phase.
    """
    db.init_db()

# ---------------------------------------------------------------------------
# Dependency: one DB session per request
# ---------------------------------------------------------------------------
def get_db() -> Generator:
    """Yield a SQLAlchemy session and ensure it is closed after the request.
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

# ---------------------------------------------------------------------------
# Authentication helper
# ---------------------------------------------------------------------------
def get_caller(request: Request) -> str:
    """Extract the caller identity from the ``Authorization`` header.

    The header must be exactly ``Bearer <token>`` where ``<token>`` matches the
    environment variable ``TOKEN_HER`` or ``TOKEN_HIM``.  Comparison uses
    :func:`hmac.compare_digest` to avoid timing attacks.  Any problem results in a
    ``401`` HTTPException with the JSON body ``{"error": "unauthorized"}``.
    """
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="unauthorized")
    token = auth[7:]  # strip "Bearer "
    token_her = os.getenv("TOKEN_HER")
    token_him = os.getenv("TOKEN_HIM")
    # Empty or unset variables never match – the ``and`` guards that.
    if token_her and hmac.compare_digest(token, token_her):
        return "her"
    if token_him and hmac.compare_digest(token, token_him):
        return "him"
    raise HTTPException(status_code=401, detail="unauthorized")

# ---------------------------------------------------------------------------
# Middleware: security headers on every response
# ---------------------------------------------------------------------------
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = "default-src 'none'"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response

# ---------------------------------------------------------------------------
# Exception handling – JSON error bodies
# ---------------------------------------------------------------------------
@app.exception_handler(HTTPException)
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc):
    # Map known status codes to the exact error messages required by the tests.
    messages = {
        401: "unauthorized",
        404: "not found",
        405: "method not allowed",
    }
    # exc may be either FastAPI's HTTPException or Starlette's HTTPException.
    # Both have ``status_code`` and ``detail`` attributes.
    message = messages.get(exc.status_code, getattr(exc, "detail", "error"))
    return JSONResponse(status_code=exc.status_code, content={"error": message})

# ---------------------------------------------------------------------------
# Public route – no authentication required
# ---------------------------------------------------------------------------
@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}

# ---------------------------------------------------------------------------
# Authenticated API routes
# ---------------------------------------------------------------------------
@app.get("/api/dashboard")
async def api_dashboard(
    caller: str = Depends(get_caller),
    session = Depends(get_db),
) -> dict:
    today = datetime.now(timezone.utc).date()
    return rules.dashboard(session, caller, today)

@app.get("/api/filed")
async def api_filed(
    caller: str = Depends(get_caller),
    session = Depends(get_db),
) -> dict:
    return {"tickets": rules.filed(session, caller)}

# The test suite also checks that unknown paths and wrong methods return the
# appropriate JSON bodies. FastAPI automatically raises ``HTTPException`` for
# those cases, and our ``http_exception_handler`` converts them to the required
# format.
