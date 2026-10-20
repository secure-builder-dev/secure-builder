import os
import hmac
import json
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
# Middleware: body size limit (413) and security headers on every response
@app.middleware("http")
async def body_size_and_security_headers(request: Request, call_next):
    # Check Content-Length header for body size limit before reading the body.
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            if int(content_length) > 65536:
                return JSONResponse(status_code=413, content={"error": "too large"})
        except ValueError:
            # If header is malformed, ignore and let the route handle it.
            pass
    # Proceed with the request.
    response = await call_next(request)
    # Add security headers to every response.
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = "default-src 'none'"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response
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
        403: "forbidden",
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


@app.get("/api/me")
async def api_me(
    caller: str = Depends(get_caller),
) -> dict:
    return {"user": caller}


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

# New route: Household board
@app.get("/api/board")
async def api_board(
    caller: str = Depends(get_caller),
    session = Depends(get_db),
) -> dict:
    """Return the household board for both users.

    The board is computed for the current UTC date so that both callers see the same
    view regardless of when they request it.
    """
    today = datetime.now(timezone.utc).date()
    # Import here to avoid circular imports at module load time.
    from app import household
    return household.household_board(session, today)

# ---------------------------------------------------------------------------
# Ticket creation route
# ---------------------------------------------------------------------------
@app.post("/api/tickets")
async def api_create_ticket(
    request: Request,
    caller: str = Depends(get_caller),
    session = Depends(get_db),
) -> JSONResponse:
    # Read and parse JSON body manually to replace FastAPI's validation.
    try:
        raw = await request.body()
        data = json.loads(raw)
    except Exception:
        return JSONResponse(status_code=400, content={"error": "invalid request"})
    if not isinstance(data, dict):
        return JSONResponse(status_code=400, content={"error": "invalid request"})
    try:
        ticket = rules.create_ticket(session, caller, data)
    except ValueError:
        return JSONResponse(status_code=400, content={"error": "invalid request"})
    return JSONResponse(status_code=201, content=ticket)

# ---------------------------------------------------------------------------
# Ticket status change route
# ---------------------------------------------------------------------------
@app.post("/api/tickets/{ticket_id}/status")
async def api_change_status(
    ticket_id: str,
    request: Request,
    caller: str = Depends(get_caller),
    session = Depends(get_db),
) -> JSONResponse:
    # Validate ticket_id is an integer.
    try:
        tid = int(ticket_id)
    except ValueError:
        return JSONResponse(status_code=400, content={"error": "invalid request"})
    # Parse JSON body.
    try:
        raw = await request.body()
        data = json.loads(raw)
    except Exception:
        return JSONResponse(status_code=400, content={"error": "invalid request"})
    if not isinstance(data, dict) or set(data.keys()) != {"status"} or not isinstance(data.get("status"), str):
        return JSONResponse(status_code=400, content={"error": "invalid request"})
    new_status = data["status"]
    try:
        ticket = rules.change_status(session, tid, caller, new_status)
    except LookupError:
        raise HTTPException(status_code=404)
    except PermissionError:
        raise HTTPException(status_code=403)
    except ValueError:
        # Invalid transition or unknown status maps to 409.
        raise HTTPException(status_code=409, detail="invalid transition")
    return JSONResponse(status_code=200, content=ticket)

# ---------------------------------------------------------------------------
# End of file
# ---------------------------------------------------------------------------