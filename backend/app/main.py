import hmac
import os
from datetime import date, datetime, timezone
from typing import Generator

from fastapi import FastAPI, Request, Depends

from app.db import SessionLocal, init_db
from app.rules import dashboard, filed, create_ticket, change_status
from app.household import household_board


def get_caller(request: Request) -> str | None:
    """Extract caller from Authorization header.
    
    Returns 'her' or 'him' based on Bearer token matching TOKEN_HER or TOKEN_HIM env vars.
    Returns None if authorization fails (caller will be checked by route).
    """
    auth_header = request.headers.get("Authorization", "")
    
    # Must be "Bearer <token>"
    if not auth_header.startswith("Bearer "):
        return None
    
    token = auth_header[7:]  # Remove "Bearer " prefix
    
    # Empty token is unauthorized
    if not token:
        return None
    
    # Read env vars on every request
    token_her = os.environ.get("TOKEN_HER", "")
    token_him = os.environ.get("TOKEN_HIM", "")
    
    # Unset or empty variable never matches
    if token_her and hmac.compare_digest(token, token_her):
        return "her"
    if token_him and hmac.compare_digest(token, token_him):
        return "him"
    
    return None


def get_session() -> Generator[SessionLocal, None, None]:
    """Provide a database session per request."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


async def lifespan(app: FastAPI):
    """Lifespan handler to initialize the database on startup."""
    init_db()
    yield



# Create FastAPI app with lifespan and middleware
app = FastAPI(lifespan=lifespan)

@app.middleware("http")
async def check_body_size_middleware(request: Request, call_next):
    """Check Content-Length header and reject bodies over 65536 bytes."""
    content_length = request.headers.get("Content-Length")
    if content_length is not None:
        try:
            if int(content_length) > 65536:
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=413,
                    content={"error": "too large"},
                    headers={
                        "X-Content-Type-Options": "nosniff",
                        "Content-Security-Policy": "default-src 'none'",
                        "Cache-Control": "no-store",
                        "Referrer-Policy": "no-referrer",
                    },
                )
        except ValueError:
            pass
    return await call_next(request)


@app.middleware("http")
async def add_security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = "default-src 'none'"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


from fastapi import HTTPException, Body
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request as StarletteRequest
import json


@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Custom handler to return JSON errors with correct format."""
    if exc.status_code == 404:
        detail = "not found"
    elif exc.status_code == 405:
        detail = "method not allowed"
    elif exc.status_code == 401:
        detail = "unauthorized"
    else:
        detail = getattr(exc, "detail", "error")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": detail},
        headers={
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'",
            "Cache-Control": "no-store",
            "Referrer-Policy": "no-referrer",
        },
    )


from fastapi.exceptions import RequestValidationError

@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle FastAPI validation errors with 400 invalid request."""
    return JSONResponse(
        status_code=400,
        content={"error": "invalid request"},
        headers={
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'",
            "Cache-Control": "no-store",
            "Referrer-Policy": "no-referrer",
        },
    )


# Routes
@app.get("/health")
def health():
    """Public health check endpoint."""
    return {"status": "ok"}


@app.get("/api/dashboard")
def get_dashboard(request: Request, session: SessionLocal = Depends(get_session)):
    """Get the caller's personal dashboard."""
    caller = get_caller(request)
    if caller is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="unauthorized")
    today = datetime.now(timezone.utc).date()
    return dashboard(session, caller, today)


@app.get("/api/filed")
def get_filed(request: Request, session: SessionLocal = Depends(get_session)):
    """Get tickets filed by the caller."""
    caller = get_caller(request)
    if caller is None:
        raise HTTPException(status_code=401, detail="unauthorized")
    return {"tickets": filed(session, caller)}


@app.post("/api/tickets", status_code=201)
async def create_ticket_route(
    request: Request,
    session: SessionLocal = Depends(get_session),
):
    """Create a new ticket."""
    caller = get_caller(request)
    if caller is None:
        raise HTTPException(status_code=401, detail="unauthorized")
    
    # Read body manually to handle validation errors
    try:
        body_bytes = await request.body()
        data = json.loads(body_bytes.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="invalid request")
    
    # Must be a JSON object
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="invalid request")
    
    try:
        result = create_ticket(session, caller, data)
        return result
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid request")


@app.get("/api/board")
def get_board(request: Request, session: SessionLocal = Depends(get_session)):
    """Get the household board with all tickets."""
    caller = get_caller(request)
    if caller is None:
        raise HTTPException(status_code=401, detail="unauthorized")
    today = datetime.now(timezone.utc).date()
    return household_board(session, today)


@app.post("/api/tickets/{ticket_id}/status")
async def change_status_route(
    ticket_id: int,
    request: Request,
    session: SessionLocal = Depends(get_session),
):
    """Change the status of a ticket."""
    caller = get_caller(request)
    if caller is None:
        raise HTTPException(status_code=401, detail="unauthorized")
    
    # Read body manually to handle validation errors
    raw_body = await request.body()
    if len(raw_body) > 65536:
        raise HTTPException(status_code=413, detail="too large")
    try:
        body_bytes = await request.body()
        data = json.loads(body_bytes.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="invalid request")
    
    # Must be exactly {"status": <string>}
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="invalid request")
    if set(data.keys()) != {"status"}:
        raise HTTPException(status_code=400, detail="invalid request")
    new_status = data["status"]
    if not isinstance(new_status, str):
        raise HTTPException(status_code=400, detail="invalid request")
    
    try:
        result = change_status(session, ticket_id, caller, new_status)
        return result
    except LookupError:
        raise HTTPException(status_code=404, detail="not found")
    except PermissionError:
        raise HTTPException(status_code=403, detail="forbidden")
    except ValueError:
        raise HTTPException(status_code=409, detail="invalid transition")
