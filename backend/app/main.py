import hmac
import os
from datetime import datetime, timezone, date
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.db import SessionLocal, init_db
from app.rules import dashboard, filed


def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    init_db()
    yield


app = FastAPI(lifespan=lifespan)


def get_caller(request: Request) -> str:
    """Extract the caller identity from the Authorization header.
    
    Reads TOKEN_HER and TOKEN_HIM from environment on every request.
    Returns 'her' or 'him' if the token matches.
    Raises HTTPException(401) for missing/invalid authorization.
    """
    auth_header = request.headers.get("Authorization", "")
    
    # Must be "Bearer <token>"
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "unauthorized"}
        )
    
    token = auth_header[7:]  # Remove "Bearer " prefix
    
    # Empty token is invalid
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "unauthorized"}
        )
    
    # Read tokens from environment on every request
    token_her = os.environ.get("TOKEN_HER", "")
    token_him = os.environ.get("TOKEN_HIM", "")
    
    # Unset or empty variables never match
    if token_her and hmac.compare_digest(token, token_her):
        return "her"
    if token_him and hmac.compare_digest(token, token_him):
        return "him"
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"error": "unauthorized"}
    )


def get_db_session():
    """Dependency that provides a database session per request."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@app.middleware("http")
async def check_body_size(request: Request, call_next):
    """Check Content-Length header and reject bodies over 65536 bytes."""
    content_length = int(request.headers.get("Content-Length", 0))
    if content_length > 65536:
        return JSONResponse(
            status_code=413,
            content={"error": "too large"}
        )
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = "default-src 'none'"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


from fastapi.exceptions import RequestValidationError

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle FastAPI validation errors with 400 invalid request."""
    return JSONResponse(
        status_code=400,
        content={"error": "invalid request"}
    )

@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions with consistent JSON format."""
    # Map status codes to error messages
    error_map = {
        404: "not found",
        405: "method not allowed",
        401: "unauthorized",
    }
    
    error_msg = error_map.get(exc.status_code, str(exc.detail))
    
    # If detail is already a dict with 'error' key, use it
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        error_msg = exc.detail["error"]
    
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": error_msg}
    )





@app.get("/health")
async def health_check():
    """Public health check endpoint."""
    return {"status": "ok"}


@app.get("/api/dashboard")
async def get_dashboard(request: Request, session: SessionLocal = Depends(get_db_session)):
    """Get the caller's personal dashboard."""
    caller = get_caller(request)
    today = datetime.now(timezone.utc).date()
    result = dashboard(session, caller, today)
    return result


@app.get("/api/filed")
async def get_filed(request: Request, session: SessionLocal = Depends(get_db_session)):
    """Get tickets filed by the caller."""
    caller = get_caller(request)
    tickets = filed(session, caller)
    return {"tickets": tickets}


@app.post("/api/tickets")
async def create_ticket_endpoint(request: Request, session: SessionLocal = Depends(get_db_session)):
    """Create a new ticket."""
    from app.rules import create_ticket
    
    caller = get_caller(request)
    
    # Read and parse the body manually to avoid FastAPI's 422
    try:
        body_bytes = await request.body()
        if len(body_bytes) > 65536:
            return JSONResponse(
                status_code=413,
                content={"error": "too large"}
            )
        body_str = body_bytes.decode("utf-8")
        import json
        data = json.loads(body_str)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JSONResponse(
            status_code=400,
            content={"error": "invalid request"}
        )
    
    # Must be a dict
    if not isinstance(data, dict):
        return JSONResponse(
            status_code=400,
            content={"error": "invalid request"}
        )
    
    try:
        result = create_ticket(session, caller, data)
        return JSONResponse(
            status_code=201,
            content=result
        )
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": "invalid request"}
        )


@app.post("/api/tickets/{id}/status")
async def change_status_endpoint(request: Request, id: int, session: SessionLocal = Depends(get_db_session)):
    """Change the status of a ticket."""
    from app.rules import change_status
    
    caller = get_caller(request)
    
    # Read and parse the body manually
    try:
        body_bytes = await request.body()
        if len(body_bytes) > 65536:
            return JSONResponse(
                status_code=413,
                content={"error": "too large"}
            )
        body_str = body_bytes.decode("utf-8")
        import json
        data = json.loads(body_str)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JSONResponse(
            status_code=400,
            content={"error": "invalid request"}
        )
    
    # Must be a dict with exactly {"status": <string>}
    if not isinstance(data, dict):
        return JSONResponse(
            status_code=400,
            content={"error": "invalid request"}
        )
    
    if set(data.keys()) != {"status"}:
        return JSONResponse(
            status_code=400,
            content={"error": "invalid request"}
        )
    
    new_status = data["status"]
    if not isinstance(new_status, str):
        return JSONResponse(
            status_code=400,
            content={"error": "invalid request"}
        )
    
    try:
        result = change_status(session, id, caller, new_status)
        return JSONResponse(
            status_code=200,
            content=result
        )
    except LookupError:
        return JSONResponse(
            status_code=404,
            content={"error": "not found"}
        )
    except PermissionError:
        return JSONResponse(
            status_code=403,
            content={"error": "forbidden"}
        )
    except ValueError:
        return JSONResponse(
            status_code=409,
            content={"error": "invalid transition"}
        )


# Remove the duplicate 404 and 405 handlers - FastAPI handles these by default
# The custom handler above already covers them via StarletteHTTPException mapping

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handle 404 errors."""
    return JSONResponse(
        status_code=404,
        content={"error": "not found"}
    )


@app.exception_handler(405)
async def method_not_allowed_handler(request: Request, exc):
    """Handle 405 errors."""
    return JSONResponse(
        status_code=405,
        content={"error": "method not allowed"}
    )


# Handle non-integer path parameter for /api/tickets/{id}/status
@app.exception_handler(422)
async def handle_422(request: Request, exc):
    """Handle 422 errors (non-integer id) with 400."""
    return JSONResponse(
        status_code=400,
        content={"error": "invalid request"}
    )

# Override the default 422 handler registration
from fastapi import FastAPI
app.add_exception_handler(422, handle_422)

# Also need to handle the case where path parameter is not an integer
# FastAPI will raise a 422 for this, which we now handle above


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handle 404 errors."""
    return JSONResponse(
        status_code=404,
        content={"error": "not found"}
    )


@app.exception_handler(405)
async def method_not_allowed_handler(request: Request, exc):
    """Handle 405 errors."""
    return JSONResponse(
        status_code=405,
        content={"error": "method not allowed"}
    )
