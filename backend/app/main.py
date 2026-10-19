import os
import hmac
import datetime
import json
from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette import status

from app import household

from app import db as db_mod
from app import rules

# New imports for ticket and activity handling
from app.models import Ticket
import app.activity as activity


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

# Replace FastAPI's default 422 validation error with a 400 JSON response


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


@app.get("/api/me")
async def api_me(
    caller: str = Depends(get_caller),
) -> dict:
    """Return the identity of the authenticated caller.

    This endpoint requires a valid bearer token and returns a JSON object
    with the key ``user`` set to either ``"her"`` or ``"him"``.
    """
    return {"user": caller}


@app.get("/health")
async def health() -> dict:
    """Public health check endpoint.

    Returns a simple JSON payload indicating the service is up.
    No authentication is required.
    """
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

@app.get("/api/board")
async def api_board(
    caller: str = Depends(get_caller),
    session=Depends(get_db),
) -> dict:
    """Return the household board for the authenticated caller.

    ``today`` is the current UTC date. The board is the same for both users.
    """
    today = datetime.datetime.now(datetime.timezone.utc).date()
    # Import here to avoid circular imports at module load time
    from app import household
    return household.household_board(session, today)


@app.get("/api/tickets/{ticket_id}")
async def get_ticket_endpoint(
    ticket_id: str,
    caller: str = Depends(get_caller),
    session=Depends(get_db),
):
    """Return a ticket by ID.

    200 with ticket dict, 404 if not found, 400 for non‑integer ID.
    """
    try:
        tid = int(ticket_id)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid request")
    ticket = session.get(Ticket, tid)
    if ticket is None:
        raise HTTPException(status_code=404, detail="not found")
    return rules.ticket_to_dict(ticket)


@app.get("/api/tickets/{ticket_id}/comments")
async def get_comments_endpoint(
    ticket_id: str,
    caller: str = Depends(get_caller),
    session=Depends(get_db),
):
    """Return comments for a ticket.

    200 with {"comments": [...]}, 404 if ticket missing, 400 for non‑integer ID.
    """
    try:
        tid = int(ticket_id)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid request")
    try:
        comments = activity.list_comments(session, tid, caller)
    except LookupError:
        raise HTTPException(status_code=404, detail="not found")
    return {"comments": comments}


@app.post("/api/tickets/{ticket_id}/comments")
async def post_comment_endpoint(
    ticket_id: str,
    request: Request,
    caller: str = Depends(get_caller),
    session=Depends(get_db),
):
    """Add a comment to a ticket.

    201 with comment dict, 404 if ticket missing, 400 for malformed request or invalid body,
    413 if body too large.
    """
    try:
        tid = int(ticket_id)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid request")
    raw = await request.body()
    if len(raw) > 65536:
        raise HTTPException(status_code=413, detail="too large")
    try:
        data = json.loads(raw)
        if not (isinstance(data, dict) and set(data.keys()) == {"body"}):
            raise ValueError
        body = data["body"]
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="invalid request")
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid request")
    try:
        comment = activity.add_comment(session, tid, caller, body)
    except LookupError:
        raise HTTPException(status_code=404, detail="not found")
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid request")
    return JSONResponse(status_code=201, content=comment)


@app.get("/api/tickets/{ticket_id}/history")
async def get_history_endpoint(
    ticket_id: str,
    caller: str = Depends(get_caller),
    session=Depends(get_db),
):
    """Return the event history for a ticket.

    200 with {"events": [...]}, 404 if ticket missing, 400 for non‑integer ID.
    """
    try:
        tid = int(ticket_id)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid request")
    try:
        events = activity.ticket_history(session, tid, caller)
    except LookupError:
        raise HTTPException(status_code=404, detail="not found")
    return {"events": events}


# ---------------------------------------------------------------------------
@app.post("/api/tickets")
async def create_ticket_endpoint(
    request: Request,
    caller: str = Depends(get_caller),
    session=Depends(get_db),
):
    # Body size limit (Content‑Length or actual size)
    raw = await request.body()
    if len(raw) > 65536:
        raise HTTPException(status_code=413, detail="too large")
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="invalid request")
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid request")

    try:
        ticket = rules.create_ticket(session, caller, data)
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid request")
    return JSONResponse(status_code=201, content=ticket)

# ---------------------------------------------------------------------------
# Ticket status change endpoint
# ---------------------------------------------------------------------------
@app.post("/api/tickets/{ticket_id}/status")
async def change_status_endpoint(
    ticket_id: str,
    request: Request,
    caller: str = Depends(get_caller),
    session=Depends(get_db),
):
    # Validate ticket_id is integer
    try:
        tid = int(ticket_id)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid request")

    raw = await request.body()
    if len(raw) > 65536:
        raise HTTPException(status_code=413, detail="too large")
    try:
        data = json.loads(raw)
        if not (isinstance(data, dict) and set(data.keys()) == {"status"} and isinstance(data["status"], str)):
            raise ValueError
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="invalid request")
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid request")

    new_status = data["status"]
    try:
        ticket = rules.change_status(session, tid, caller, new_status)
        return ticket
    except LookupError:
        raise HTTPException(status_code=404, detail="not found")
    except PermissionError:
        raise HTTPException(status_code=403, detail="forbidden")
    except ValueError:
        # Invalid transition (or invalid status) maps to 409 per spec
        raise HTTPException(status_code=409, detail="invalid transition")
