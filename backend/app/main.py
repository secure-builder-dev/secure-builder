import os
import json
import hmac
from typing import Any
from datetime import date, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session

from app.db import SessionLocal, init_db
from app.rules import create_ticket, change_status, dashboard, filed


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)


def get_caller(request: Request) -> str:
    """Extract caller from Authorization header using Bearer token.
    
    Returns 'her' if token matches TOKEN_HER env var,
    Returns 'him' if token matches TOKEN_HIM env var.
    Raises HTTPException 401 otherwise.
    """
    auth_header = request.headers.get("Authorization", "")
    
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="unauthorized"
        )
    
    token = auth_header[7:]  # Remove "Bearer " prefix
    
    token_her = os.environ.get("TOKEN_HER", "")
    token_him = os.environ.get("TOKEN_HIM", "")
    
    if token_her and hmac.compare_digest(token, token_her):
        return "her"
    if token_him and hmac.compare_digest(token, token_him):
        return "him"
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="unauthorized"
    )


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = "default-src 'none'"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    response = JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": "invalid request"},
        headers={
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'",
            "Cache-Control": "no-store",
            "Referrer-Policy": "no-referrer"
        }
    )
    return response


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    # Never expose stack traces
    response = JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "internal error"},
        headers={
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'",
            "Cache-Control": "no-store",
            "Referrer-Policy": "no-referrer"
        }
    )
    return response


@app.post("/api/tickets", status_code=status.HTTP_201_CREATED)
async def create_ticket_endpoint(request: Request):
    caller = get_caller(request)
    
    # Read raw body to check size and parse JSON manually
    try:
        body_bytes = await request.body()
    except Exception:
        response = JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "invalid request"},
            headers={
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": "default-src 'none'",
                "Cache-Control": "no-store",
                "Referrer-Policy": "no-referrer"
            }
        )
        return response
    
    if len(body_bytes) > 65536:
        response = JSONResponse(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            content={"error": "too large"},
            headers={
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": "default-src 'none'",
                "Cache-Control": "no-store",
                "Referrer-Policy": "no-referrer"
            }
        )
        return response
    
    try:
        body_str = body_bytes.decode("utf-8")
        data = json.loads(body_str)
        if not isinstance(data, dict):
            raise ValueError("Body must be a JSON object")
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as e:
        response = JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "invalid request"},
            headers={
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": "default-src 'none'",
                "Cache-Control": "no-store",
                "Referrer-Policy": "no-referrer"
            }
        )
        return response
    
    session: Session = SessionLocal()
    try:
        result = create_ticket(session, caller, data)
        session.commit()
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content=result,
            headers={
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": "default-src 'none'",
                "Cache-Control": "no-store",
                "Referrer-Policy": "no-referrer"
            }
        )
    except ValueError as e:
        session.rollback()
        response = JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "invalid request"},
            headers={
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": "default-src 'none'",
                "Cache-Control": "no-store",
                "Referrer-Policy": "no-referrer"
            }
        )
        return response
    finally:
        session.close()


@app.post("/api/tickets/{ticket_id}/status")
async def change_status_endpoint(request: Request, ticket_id: int):
    caller = get_caller(request)
    
    # Read raw body to check size and parse JSON manually
    try:
        body_bytes = await request.body()
    except Exception:
        response = JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "invalid request"},
            headers={
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": "default-src 'none'",
                "Cache-Control": "no-store",
                "Referrer-Policy": "no-referrer"
            }
        )
        return response
    
    if len(body_bytes) > 65536:
        response = JSONResponse(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            content={"error": "too large"},
            headers={
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": "default-src 'none'",
                "Cache-Control": "no-store",
                "Referrer-Policy": "no-referrer"
            }
        )
        return response
    
    try:
        body_str = body_bytes.decode("utf-8")
        data = json.loads(body_str)
        if not isinstance(data, dict):
            raise ValueError("Body must be a JSON object")
        new_status = data.get("status")
        if new_status is None or not isinstance(new_status, str):
            raise ValueError("status field required")
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as e:
        response = JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "invalid request"},
            headers={
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": "default-src 'none'",
                "Cache-Control": "no-store",
                "Referrer-Policy": "no-referrer"
            }
        )
        return response
    
    session: Session = SessionLocal()
    try:
        result = change_status(session, ticket_id, caller, new_status)
        session.commit()
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=result,
            headers={
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": "default-src 'none'",
                "Cache-Control": "no-store",
                "Referrer-Policy": "no-referrer"
            }
        )
    except LookupError:
        session.rollback()
        response = JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "not found"},
            headers={
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": "default-src 'none'",
                "Cache-Control": "no-store",
                "Referrer-Policy": "no-referrer"
            }
        )
        return response
    except PermissionError:
        session.rollback()
        response = JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"error": "forbidden"},
            headers={
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": "default-src 'none'",
                "Cache-Control": "no-store",
                "Referrer-Policy": "no-referrer"
            }
        )
        return response
    except ValueError:
        session.rollback()
        response = JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"error": "invalid transition"},
            headers={
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": "default-src 'none'",
                "Cache-Control": "no-store",
                "Referrer-Policy": "no-referrer"
            }
        )
        return response
    finally:
        session.close()


@app.get("/api/dashboard")
def dashboard_endpoint(request: Request):
    caller = get_caller(request)
    today = date.today()
    
    session: Session = SessionLocal()
    try:
        result = dashboard(session, caller, today)
        return JSONResponse(
            content=result,
            headers={
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": "default-src 'none'",
                "Cache-Control": "no-store",
                "Referrer-Policy": "no-referrer"
            }
        )
    finally:
        session.close()


@app.get("/api/filed")
def filed_endpoint(request: Request):
    caller = get_caller(request)
    
    session: Session = SessionLocal()
    try:
        tickets = filed(session, caller)
        return JSONResponse(
            content={"tickets": tickets},
            headers={
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": "default-src 'none'",
                "Cache-Control": "no-store",
                "Referrer-Policy": "no-referrer"
            }
        )
    finally:
        session.close()


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    # Never expose stack traces
    response = JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "internal error"},
        headers={
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'",
            "Cache-Control": "no-store",
            "Referrer-Policy": "no-referrer"
        }
    )
    return response


@app.exception_handler(404)
async def custom_404_handler(request: Request, exc: Exception):
    response = JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"error": "not found"},
        headers={
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'",
            "Cache-Control": "no-store",
            "Referrer-Policy": "no-referrer"
        }
    )
    return response


@app.exception_handler(405)
async def custom_405_handler(request: Request, exc: Exception):
    response = JSONResponse(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        content={"error": "method not allowed"},
        headers={
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'",
            "Cache-Control": "no-store",
            "Referrer-Policy": "no-referrer"
        }
    )
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    headers = {
        "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "default-src 'none'",
        "Cache-Control": "no-store",
        "Referrer-Policy": "no-referrer"
    }
    # Convert FastAPI's detail to error key for 401 responses
    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": "unauthorized"},
            headers=headers
        )
    # For other HTTPExceptions, use the detail as error
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail if isinstance(exc.detail, str) else "error"},
        headers=headers
    )
