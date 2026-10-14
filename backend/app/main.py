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
async def add_security_headers(request: Request, call_next):
    """Add security headers to every response."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = "default-src 'none'"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


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
