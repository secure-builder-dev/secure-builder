import hmac
import os
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse

from app.db import SessionLocal, init_db
from app.rules import dashboard, filed

from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan_handler(app: FastAPI):
    """Initialize the database on startup."""
    init_db()
    yield


app = FastAPI(lifespan=lifespan_handler)


def get_caller(request: StarletteRequest) -> Optional[str]:
    """
    Extract the caller from the Authorization header.
    
    Returns 'her' if token matches TOKEN_HER, 'him' if token matches TOKEN_HIM.
    Returns None if authorization is missing, invalid, or doesn't match.
    """
    auth_header = request.headers.get("Authorization", "")
    
    # Check for Bearer scheme
    if not auth_header.startswith("Bearer "):
        return None
    
    token = auth_header[7:]  # Remove "Bearer " prefix
    
    # Empty token is invalid
    if not token:
        return None
    
    # Read tokens from environment on every request
    token_her = os.environ.get("TOKEN_HER", "")
    token_him = os.environ.get("TOKEN_HIM", "")
    
    # Unset or empty variables never match
    if not token_her and not token_him:
        return None
    
    # Compare with hmac.compare_digest
    if token_her and hmac.compare_digest(token, token_her):
        return "her"
    if token_him and hmac.compare_digest(token, token_him):
        return "him"
    
    return None


def require_caller(request: StarletteRequest) -> str:
    """
    Get the caller or raise HTTPException 401.
    """
    caller = get_caller(request)
    if caller is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "unauthorized"}
        )
    return caller


# Middleware for security headers
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "default-src 'none'"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response


app.add_middleware(SecurityHeadersMiddleware)


# Exception handler for HTTPException (404, 405, etc.)
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: StarletteRequest, exc: StarletteHTTPException):
    # Map status codes to error messages
    if exc.status_code == 404:
        return JSONResponse(
            status_code=404,
            content={"error": "not found"}
        )
    elif exc.status_code == 405:
        return JSONResponse(
            status_code=405,
            content={"error": "method not allowed"}
        )
    else:
        # For other HTTPExceptions, use the detail from the exception
        if isinstance(exc.detail, dict):
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": str(exc.detail)}
        )





@app.get("/health")
def health_check():
    """Public health check endpoint."""
    return {"status": "ok"}


@app.get("/api/dashboard")
def get_dashboard(request: StarletteRequest):
    """Get the caller's personal dashboard."""
    caller = require_caller(request)
    session = SessionLocal()
    try:
        today = datetime.now(timezone.utc).date()
        result = dashboard(session, caller, today)
        return result
    finally:
        session.close()


@app.get("/api/filed")
def get_filed(request: StarletteRequest):
    """Get tickets filed by the caller."""
    caller = require_caller(request)
    session = SessionLocal()
    try:
        tickets = filed(session, caller)
        return {"tickets": tickets}
    finally:
        session.close()
