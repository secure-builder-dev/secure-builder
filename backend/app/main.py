import json
import os
from datetime import date, timezone
from typing import Any

import hmac
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse
from contextlib import asynccontextmanager

from app.db import SessionLocal, init_db
from app.rules import create_ticket, change_status, dashboard, filed, USERS
from app.household import household_board

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(lifespan=lifespan)


def get_caller(request: Request) -> str:
    """Extract caller identity from Authorization header.
    
    Returns 'her' or 'him' based on TOKEN_HER/TOKEN_HIM env vars.
    Raises HTTPException 401 if missing, invalid, or env var unset/empty.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="unauthorized")
    
    token = auth_header[7:]  # Remove "Bearer " prefix
    
    token_her = os.environ.get("TOKEN_HER", "")
    token_him = os.environ.get("TOKEN_HIM", "")
    
    if not token_her or not token_him:
        raise HTTPException(status_code=401, detail="unauthorized")
    
    if hmac.compare_digest(token, token_her):
        return "her"
    if hmac.compare_digest(token, token_him):
        return "him"
    
    raise HTTPException(status_code=401, detail="unauthorized")


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = "default-src 'none'"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.middleware("http")
async def check_body_size(request: Request, call_next):
    content_length = request.headers.get("Content-Length", "0")
    try:
        if int(content_length) > 65536:
            return JSONResponse(
                status_code=413,
                content={"error": "too large"}
            )
    except ValueError:
        pass
    return await call_next(request)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={"error": "invalid request"}
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    # Never expose stack traces
    if isinstance(exc.detail, dict):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail.get("error", "error")}
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": str(exc.detail)}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    # Never expose stack traces
    return JSONResponse(
        status_code=500,
        content={"error": "internal error"}
    )





@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/api/tickets", status_code=201)
async def create_ticket_endpoint(request: Request):
    caller = get_caller(request)
    
    try:
        body_bytes = await request.body()
        if len(body_bytes) == 0:
            return JSONResponse(status_code=400, content={"error": "invalid request"})
        data = json.loads(body_bytes.decode("utf-8"))
        if not isinstance(data, dict):
            return JSONResponse(status_code=400, content={"error": "invalid request"})
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JSONResponse(status_code=400, content={"error": "invalid request"})
    
    session = SessionLocal()
    try:
        result = create_ticket(session, caller, data)
        return JSONResponse(status_code=201, content=result)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": "invalid request"})
    finally:
        session.close()


@app.post("/api/tickets/{ticket_id}/status")
async def change_status_endpoint(request: Request, ticket_id: int):
    caller = get_caller(request)
    
    try:
        body_bytes = await request.body()
        data = json.loads(body_bytes.decode("utf-8"))
        if not isinstance(data, dict):
            return JSONResponse(status_code=400, content={"error": "invalid request"})
        new_status = data.get("status")
        if not isinstance(new_status, str):
            return JSONResponse(status_code=400, content={"error": "invalid request"})
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JSONResponse(status_code=400, content={"error": "invalid request"})
    
    session = SessionLocal()
    try:
        result = change_status(session, ticket_id, caller, new_status)
        return JSONResponse(status_code=200, content=result)
    except LookupError:
        return JSONResponse(status_code=404, content={"error": "not found"})
    except PermissionError:
        return JSONResponse(status_code=403, content={"error": "forbidden"})
    except ValueError:
        return JSONResponse(status_code=409, content={"error": "invalid transition"})
    finally:
        session.close()


@app.get("/api/dashboard")
async def dashboard_endpoint(request: Request):
    caller = get_caller(request)
    today = date.today()
    
    session = SessionLocal()
    try:
        result = dashboard(session, caller, today)
        return JSONResponse(status_code=200, content=result)
    finally:
        session.close()


@app.get("/api/filed")
async def filed_endpoint(request: Request):
    from app.db import init_db, Base, engine
    caller = get_caller(request)
    
    # Ensure tables exist (for test environments without lifespan)
    Base.metadata.create_all(bind=engine)
    
    session = SessionLocal()
    try:
        tickets = filed(session, caller)
        return JSONResponse(status_code=200, content={"tickets": tickets})
    finally:
        session.close()


@app.get("/api/board")
async def board_endpoint(request: Request):
    caller = get_caller(request)
    today = date.today()
    
    session = SessionLocal()
    try:
        result = household_board(session, today)
        return JSONResponse(status_code=200, content=result)
    finally:
        session.close()


@app.exception_handler(404)
async def custom_404_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "not found"}
    )


@app.exception_handler(405)
async def custom_405_handler(request: Request, exc):
    return JSONResponse(
        status_code=405,
        content={"error": "method not allowed"}
    )