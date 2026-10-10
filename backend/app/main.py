import os
import hmac
from datetime import date
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware import Middleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import sessionmaker
from app.db import engine, init_db
from app.rules import create_ticket, change_status, dashboard, filed
from app.household import household_board

app = FastAPI()

# Database session middleware
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    response = None
    try:
        request.state.db = SessionLocal()
        response = await call_next(request)
    finally:
        if request.state.db:
            request.state.db.close()
    return response

# Security headers middleware
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = "default-src 'none'"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response

# Body size limit middleware
@app.middleware("http")
async def body_size_limit_middleware(request: Request, call_next):
    if request.method in ("POST", "PUT", "PATCH") and "content-length" in request.headers:
        content_length = int(request.headers["content-length"])
        if content_length > 65536:
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={"error": "too large"}
            )
    return await call_next(request)

# Custom exception handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": "invalid request"}
    )

# Custom exception handler for HTTP exceptions
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )

# Custom exception handler for all other exceptions
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "internal server error"}
    )

def get_caller(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="unauthorized"
        )
    
    token = auth_header.split(" ")[1]
    her_token = os.environ.get("TOKEN_HER")
    him_token = os.environ.get("TOKEN_HIM")
    
    if not her_token or not him_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="unauthorized"
        )
    
    if hmac.compare_digest(token, her_token):
        return "her"
    elif hmac.compare_digest(token, him_token):
        return "him"
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="unauthorized"
        )

@app.on_event("startup")
async def startup_event():
    init_db()

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/api/tickets")
async def create_ticket_endpoint(request: Request):
    caller = get_caller(request)
    try:
        data = await request.json()
        if not isinstance(data, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid request"
            )
        ticket = create_ticket(request.state.db, caller, data)
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content=ticket
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid request"
        )

@app.post("/api/tickets/{ticket_id}/status")
async def update_ticket_status(ticket_id: int, request: Request):
    caller = get_caller(request)
    try:
        data = await request.json()
        if not isinstance(data, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid request"
            )
        new_status = data.get("status")
        if new_status is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid request"
            )
        ticket = change_status(request.state.db, ticket_id, caller, new_status)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=ticket
        )
    except LookupError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="not found"
        )
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="forbidden"
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="invalid transition"
        )

@app.get("/api/dashboard")
async def dashboard_endpoint(request: Request):
    caller = get_caller(request)
    today = date.today()
    dash = dashboard(request.state.db, caller, today)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=dash
    )

@app.get("/api/filed")
async def filed_endpoint(request: Request):
    caller = get_caller(request)
    tickets = filed(request.state.db, caller)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"tickets": tickets}
    )

@app.get("/api/board")
async def board_endpoint(request: Request):
    caller = get_caller(request)
    today = date.today()
    board = household_board(request.state.db, today)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=board
    )

@app.get("/api/me")
async def me_endpoint(request: Request):
    caller = get_caller(request)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"user": caller}
    )

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def catch_all(path: str, request: Request):
    if request.method == "GET":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="not found"
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
            detail="method not allowed"
        )