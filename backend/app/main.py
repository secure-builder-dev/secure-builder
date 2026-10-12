import hmac
import os
from datetime import date, datetime, timezone
from typing import Generator

from fastapi import FastAPI, Request, Depends

from app.db import SessionLocal, init_db
from app.rules import dashboard, filed


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
async def add_security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = "default-src 'none'"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


from fastapi import HTTPException
from starlette.exceptions import HTTPException as StarletteHTTPException


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
    
    from fastapi.responses import JSONResponse
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
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="unauthorized")
    return {"tickets": filed(session, caller)}
