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
from app.models import Ticket

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
    q: str | None = None,
    priority: str | None = None,
    assigned_to: str | None = None,
) -> dict:
    """Return the household board for both users, optionally filtered.

    The optional query parameters ``q``, ``priority`` and ``assigned_to`` are
    validated according to the design:
    * ``q`` – if present, must be at most 120 characters.
    * ``priority`` – if present, must be one of ``low``, ``normal`` or ``urgent``.
    * ``assigned_to`` – if present, must be ``her`` or ``him``.
    Any validation failure results in a ``400`` response with the JSON body
    ``{"error": "invalid request"}``.  Other query parameters are ignored.
    """
    # Validate query parameters.
    # Treat empty strings as not provided.
    if q == "":
        q = None
    if priority == "":
        priority = None
    if assigned_to == "":
        assigned_to = None
    if q is not None and len(q) > 120:
        return JSONResponse(status_code=400, content={"error": "invalid request"})
    if priority is not None and priority not in {"low", "normal", "urgent"}:
        return JSONResponse(status_code=400, content={"error": "invalid request"})
    if assigned_to is not None and assigned_to not in {"her", "him"}:
        return JSONResponse(status_code=400, content={"error": "invalid request"})

    today = datetime.now(timezone.utc).date()
    # Import here to avoid circular imports at module load time.
    from app import household
    return household.household_board(session, today, q=q, priority=priority, assigned_to=assigned_to)

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
# Ticket detail routes (E3)
# ---------------------------------------------------------------------------

from app.activity import add_comment, list_comments, ticket_history

@app.get("/api/tickets/{ticket_id}")
async def api_get_ticket(
    ticket_id: str,
    caller: str = Depends(get_caller),
    session = Depends(get_db),
) -> JSONResponse:
    """Return a single ticket by id.

    200 with the ticket dict, 404 if not found, 400 if id not an integer.
    """
    try:
        tid = int(ticket_id)
    except ValueError:
        return JSONResponse(status_code=400, content={"error": "invalid request"})
    # Fetch ticket and ensure caller is a party.
    ticket = session.get(Ticket, tid)
    if ticket is None or caller not in (ticket.filed_by, ticket.assigned_to):
        raise HTTPException(status_code=404)
    return JSONResponse(status_code=200, content=rules.ticket_to_dict(ticket))

@app.get("/api/tickets/{ticket_id}/comments")
async def api_get_comments(
    ticket_id: str,
    caller: str = Depends(get_caller),
    session = Depends(get_db),
) -> JSONResponse:
    """Return comments for a ticket.

    200 with {"comments": [...]}, 404 if ticket missing, 400 if id not integer.
    """
    try:
        tid = int(ticket_id)
    except ValueError:
        return JSONResponse(status_code=400, content={"error": "invalid request"})
    try:
        comments = list_comments(session, tid, caller)
    except LookupError:
        raise HTTPException(status_code=404)
    return JSONResponse(status_code=200, content={"comments": comments})

@app.post("/api/tickets/{ticket_id}/comments")
async def api_post_comment(
    ticket_id: str,
    request: Request,
    caller: str = Depends(get_caller),
    session = Depends(get_db),
) -> JSONResponse:
    """Add a comment to a ticket.

    201 with the comment dict, 400 for malformed/invalid request, 404 if ticket missing.
    """
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
    if not isinstance(data, dict) or set(data.keys()) != {"body"}:
        return JSONResponse(status_code=400, content={"error": "invalid request"})
    body = data["body"]
    try:
        comment = add_comment(session, tid, caller, body)
    except LookupError:
        raise HTTPException(status_code=404)
    except ValueError:
        return JSONResponse(status_code=400, content={"error": "invalid request"})
    return JSONResponse(status_code=201, content=comment)

@app.get("/api/tickets/{ticket_id}/history")
async def api_get_history(
    ticket_id: str,
    caller: str = Depends(get_caller),
    session = Depends(get_db),
) -> JSONResponse:
    """Return the event history for a ticket.

    200 with {"events": [...]}, 404 if ticket missing, 400 if id not integer.
    """
    try:
        tid = int(ticket_id)
    except ValueError:
        return JSONResponse(status_code=400, content={"error": "invalid request"})
    try:
        events = ticket_history(session, tid, caller)
    except LookupError:
        raise HTTPException(status_code=404)
    return JSONResponse(status_code=200, content={"events": events})


@app.patch("/api/tickets/{ticket_id}")
async def api_edit_ticket(
    ticket_id: str,
    request: Request,
    caller: str = Depends(get_caller),
    session = Depends(get_db),
) -> JSONResponse:
    """Edit a ticket.

    200 with the edited ticket dict, 404 if not found, 400 for malformed/invalid request,
    403 if caller is not the filer, 409 if ticket status is not editable.
    """
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
    if not isinstance(data, dict):
        return JSONResponse(status_code=400, content={"error": "invalid request"})
    try:
        ticket = rules.edit_ticket(session, tid, caller, data)
    except LookupError:
        raise HTTPException(status_code=404)
    except PermissionError:
        raise HTTPException(status_code=403)
    except ValueError:
        return JSONResponse(status_code=400, content={"error": "invalid request"})
    except rules.NotEditable:
        raise HTTPException(status_code=409, detail="not editable")
    return JSONResponse(status_code=200, content=ticket)


@app.get("/api/summary")
async def api_summary(
    caller: str = Depends(get_caller),
    session = Depends(get_db),
) -> dict:
    """Return the summary for the caller.

    200 with a dict containing ``overdue``, ``due_today`` and ``open`` counts.
    401 if the bearer token is missing or invalid.
    """
    today = datetime.now(timezone.utc).date()
    from app import household
    return household.summary(session, caller, today)

# ---------------------------------------------------------------------------