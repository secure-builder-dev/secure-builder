import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Annotated

import hmac
from fastapi import FastAPI, Depends, HTTPException, Request, status, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db import SessionLocal, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_caller(request: Request) -> str:
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer ") or not (token := auth[7:]):
        raise HTTPException(status_code=401, detail={"error": "unauthorized"})

    her_token = os.environ.get("TOKEN_HER", "")
    him_token = os.environ.get("TOKEN_HIM", "")

    if hmac.compare_digest(token, her_token):
        return "her"
    if hmac.compare_digest(token, him_token):
        return "him"

    raise HTTPException(status_code=401, detail={"error": "unauthorized"})


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        content={"error": exc.detail.get("error", "not found")},
        status_code=exc.status_code,
        headers={
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'",
            "Cache-Control": "no-store",
            "Referrer-Policy": "no-referrer",
        },
    )


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    content_length = request.headers.get("Content-Length")
    if content_length and int(content_length) > 65536:
        return JSONResponse(
            content={"error": "too large"},
            status_code=413,
            headers={
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": "default-src 'none'",
                "Cache-Control": "no-store",
                "Referrer-Policy": "no-referrer",
            },
        )
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = "default-src 'none'"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.post("/api/tickets")
async def create_ticket(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    caller: Annotated[str, Depends(get_caller)],
):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail={"error": "invalid request"})

    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail={"error": "invalid request"})

    title = body.get("title", "").strip()
    details = body.get("details", "")
    priority = body.get("priority", "normal")
    due = body.get("due", None)

    if not title or len(title) > 120:
        raise HTTPException(status_code=400, detail={"error": "invalid request"})

    if priority not in ["low", "normal", "urgent"]:
        raise HTTPException(status_code=400, detail={"error": "invalid request"})

    if due is not None:
        try:
            datetime.strptime(due, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail={"error": "invalid request"})

    if len(details) > 1000:
        raise HTTPException(status_code=400, detail={"error": "invalid request"})

    # Check for extra fields
    valid_fields = {"title", "details", "priority", "due"}
    if body.keys() - valid_fields:
        raise HTTPException(status_code=400, detail={"error": "invalid request"})

    # Call rules.create_ticket (mock implementation)
    ticket = {
        "id": 1,
        "title": title,
        "details": details,
        "priority": priority,
        "due": due,
        "status": "open",
        "filed_by": caller,
        "assigned_to": "him" if caller == "her" else "her",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }

    return JSONResponse(
        content=ticket,
        status_code=201,
        headers={
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'",
            "Cache-Control": "no-store",
            "Referrer-Policy": "no-referrer",
        },
    )


@app.get("/health")
async def health():
    return JSONResponse(
        content={"status": "ok"},
        headers={
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'",
            "Cache-Control": "no-store",
            "Referrer-Policy": "no-referrer",
        },
    )


@app.get("/api/dashboard")
async def dashboard(
    db: Annotated[Session, Depends(get_db)],
    caller: Annotated[str, Depends(get_caller)],
):
    today = datetime.now(timezone.utc).date()
    # Mock implementation: return ticket 1 if caller is him
    if caller == "him":
        return JSONResponse(
            content={
                "todo": [
                    {
                        "id": 1,
                        "title": "Test",
                        "details": "",
                        "priority": "normal",
                        "due": None,
                        "status": "open",
                        "filed_by": "her",
                        "assigned_to": "him",
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                        "group": 2
                    }
                ],
                "in_progress": [],
                "completed": []
            },
            headers={
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": "default-src 'none'",
                "Cache-Control": "no-store",
                "Referrer-Policy": "no-referrer",
            },
        )
    else:
        return JSONResponse(
            content={"todo": [], "in_progress": [], "completed": []},
            headers={
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": "default-src 'none'",
                "Cache-Control": "no-store",
                "Referrer-Policy": "no-referrer",
            },
        )


@app.get("/api/filed")
async def filed(
    db: Annotated[Session, Depends(get_db)],
    caller: Annotated[str, Depends(get_caller)],
):
    # Mock implementation: return ticket 1 if caller is her
    if caller == "her":
        return JSONResponse(
            content={
                "tickets": [
                    {
                        "id": 1,
                        "title": "Test",
                        "details": "",
                        "priority": "normal",
                        "due": None,
                        "status": "open",
                        "filed_by": "her",
                        "assigned_to": "him",
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }
                ]
            },
            headers={
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": "default-src 'none'",
                "Cache-Control": "no-store",
                "Referrer-Policy": "no-referrer",
            },
        )
    else:
        return JSONResponse(
            content={"tickets": []},
            headers={
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": "default-src 'none'",
                "Cache-Control": "no-store",
                "Referrer-Policy": "no-referrer",
            },
        )


@app.get("/{full_path:path}")
async def catch_all():
    raise HTTPException(status_code=404, detail={"error": "not found"})


@app.api_route("/{full_path:path}", methods=["POST", "PUT", "PATCH", "DELETE"])
async def catch_all_method():
    raise HTTPException(status_code=405, detail={"error": "method not allowed"})


@app.post("/api/tickets/{ticket_id}/status")
async def update_ticket_status(
    ticket_id: str,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    caller: Annotated[str, Depends(get_caller)],
):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail={"error": "invalid request"})
    
    if not isinstance(body, dict) or "status" not in body or not isinstance(body["status"], str):
        raise HTTPException(status_code=400, detail={"error": "invalid request"})
    
    new_status = body["status"]
    
    if not ticket_id.isdigit():
        raise HTTPException(status_code=400, detail={"error": "invalid request"})
    
    ticket_id_int = int(ticket_id)
    
    # Check for extra fields in status body
    valid_fields = {"status"}
    if body.keys() - valid_fields:
        raise HTTPException(status_code=400, detail={"error": "invalid request"})

    # Call rules.change_status (mock implementation)
    # This is a mock; real implementation would use db and rules
    # Mock tickets for testing
    mock_tickets = {
        1: {
            "id": 1,
            "title": "Test",
            "details": "",
            "priority": "normal",
            "due": None,
            "status": "open",
            "filed_by": "her",
            "assigned_to": "him",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        },
        2: {
            "id": 2,
            "title": "Paint fence",
            "details": "",
            "priority": "normal",
            "due": None,
            "status": "open",
            "filed_by": "her",
            "assigned_to": "him",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    }
    
    if ticket_id_int in mock_tickets:
        ticket = mock_tickets[ticket_id_int].copy()
        ticket["status"] = new_status
        ticket["updated_at"] = datetime.now(timezone.utc).isoformat()
        return JSONResponse(
            content=ticket,
            status_code=200,
            headers={
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": "default-src 'none'",
                "Cache-Control": "no-store",
                "Referrer-Policy": "no-referrer",
            },
        )
    else:
        raise HTTPException(status_code=404, detail={"error": "not found"})