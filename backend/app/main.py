import hmac
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route

from app.db import SessionLocal, init_db


def get_caller(request: Request) -> Optional[str]:
    """Read Authorization header and return 'her' or 'him', or None if invalid."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth[7:]  # len("Bearer ") == 7
    if not token:
        return None

    token_her = os.environ.get("TOKEN_HER", "")
    token_him = os.environ.get("TOKEN_HIM", "")

    if token_her and hmac.compare_digest(token, token_her):
        return "her"
    if token_him and hmac.compare_digest(token, token_him):
        return "him"
    return None


def get_session():
    """Yield a database session per request."""
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


def health_endpoint(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


def api_dashboard(request: Request) -> JSONResponse:
    caller = get_caller(request)
    if caller is None:
        raise HTTPException(status_code=401, detail="unauthorized")

    s = SessionLocal()
    try:
        today = datetime.now(timezone.utc).date()
        board = _dashboard_impl(s, caller, today)
        return JSONResponse(board)
    finally:
        s.close()


def api_filed(request: Request) -> JSONResponse:
    caller = get_caller(request)
    if caller is None:
        raise HTTPException(status_code=401, detail="unauthorized")

    s = SessionLocal()
    try:
        tickets = _filed_impl(s, caller)
        return JSONResponse({"tickets": tickets})
    finally:
        s.close()


def _dashboard_impl(session, caller: str, today):
    """Implement dashboard logic inline."""
    from app.models import Ticket
    from sqlalchemy import and_, or_, func, date
    
    # Tickets assigned to caller
    assigned = session.query(Ticket).filter(Ticket.assigned_to == caller).all()
    
    todo = []
    in_progress = []
    completed = []
    
    seven_days_ago = today - datetime.timedelta(days=7) if hasattr(datetime, 'timedelta') else __import__('datetime').timedelta(days=7)
    from datetime import timedelta
    seven_days_ago = today - timedelta(days=7)
    
    for t in assigned:
        # Convert ticket to dict-like structure
        ticket_dict = {
            "id": t.id,
            "title": t.title,
            "details": t.details,
            "priority": t.priority,
            "due": t.due.isoformat() if t.due else None,
            "status": t.status,
            "filed_by": t.filed_by,
            "assigned_to": t.assigned_to,
            "created_at": t.created_at.isoformat(),
            "updated_at": t.updated_at.isoformat(),
        }
        
        if t.status in ("open", "acknowledged"):
            # Determine group
            due_before = t.due is not None and t.due < today
            due_today_or_3days = (
                t.due is not None and 
                t.due >= today and 
                t.due <= today + timedelta(days=3)
            )
            if t.priority == "urgent" or due_before:
                ticket_dict["group"] = 0
            elif due_today_or_3days:
                ticket_dict["group"] = 1
            else:
                ticket_dict["group"] = 2
            todo.append(ticket_dict)
        elif t.status == "in_progress":
            # Determine group
            due_before = t.due is not None and t.due < today
            due_today_or_3days = (
                t.due is not None and 
                t.due >= today and 
                t.due <= today + timedelta(days=3)
            )
            if t.priority == "urgent" or due_before:
                ticket_dict["group"] = 0
            elif due_today_or_3days:
                ticket_dict["group"] = 1
            else:
                ticket_dict["group"] = 2
            in_progress.append(ticket_dict)
        elif t.status in ("done", "closed"):
            # Check if updated_at is within last 7 days
            update_date = t.updated_at.date()
            if update_date >= seven_days_ago and update_date <= today:
                completed.append(ticket_dict)
    
    # Sort todo: group, then due (none last), then created_at
    def sort_key(t):
        g = t.get("group", 2)
        due = t["due"]
        if due is None:
            due_sort = "9999-12-31"
        else:
            due_sort = due
        return (g, due_sort, t["created_at"])
    
    todo.sort(key=sort_key)
    in_progress.sort(key=sort_key)
    completed.sort(key=lambda t: t["updated_at"], reverse=True)
    
    return {"todo": todo, "in_progress": in_progress, "completed": completed}


def _filed_impl(session, caller: str):
    """Implement filed tickets logic inline."""
    from app.models import Ticket
    
    tickets = session.query(Ticket).filter(Ticket.filed_by == caller).order_by(Ticket.created_at.desc()).all()
    
    result = []
    for t in tickets:
        ticket_dict = {
            "id": t.id,
            "title": t.title,
            "details": t.details,
            "priority": t.priority,
            "due": t.due.isoformat() if t.due else None,
            "status": t.status,
            "filed_by": t.filed_by,
            "assigned_to": t.assigned_to,
            "created_at": t.created_at.isoformat(),
            "updated_at": t.updated_at.isoformat(),
        }
        result.append(ticket_dict)
    
    return result


# Define routes
routes: list[Route] = [
    Route("/health", endpoint=health_endpoint, methods=["GET"]),
    Route("/api/dashboard", endpoint=api_dashboard, methods=["GET"]),
    Route("/api/filed", endpoint=api_filed, methods=["GET"]),
]

app = FastAPI()
app.router.routes = routes

# Add middleware
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = "default-src 'none'"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response

app.add_middleware(BaseHTTPMiddleware, dispatch=add_security_headers)

# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    content = {"error": exc.detail} if isinstance(exc.detail, str) else {"error": "error"}
    return JSONResponse(
        status_code=exc.status_code,
        content=content
    )

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "not found"}
    )

@app.exception_handler(405)
async def method_not_allowed_handler(request: Request, exc):
    return JSONResponse(
        status_code=405,
        content={"error": "method not allowed"}
    )

# Lifespan handler for startup
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan_handler(app):
    init_db()
    yield

app.router.lifespan_context = lifespan_handler
