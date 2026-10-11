from fastapi import FastAPI, Request, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
from hmac import compare_digest
from app.db import init_db, SessionLocal
from app.rules import create_ticket, change_status, dashboard, filed
from app.household import household_board
from datetime import date

app = FastAPI()

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = "default-src 'none'"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response

# Body size limit
@app.middleware("http")
async def check_body_size(request: Request, call_next):
    if request.method in ("POST", "PUT", "PATCH") and request.headers.get("content-length") and int(request.headers["content-length"]) > 65536:
        return JSONResponse(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content={"error": "too large"}
        )
    return await call_next(request)

# Database session dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Authentication dependency
def get_caller(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"error": "unauthorized"})
    
    token = auth_header.split(" ", 1)[1]
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"error": "unauthorized"})
    
    her_token = os.getenv("TOKEN_HER")
    him_token = os.getenv("TOKEN_HIM")
    
    if her_token and compare_digest(token, her_token):
        return "her"
    elif him_token and compare_digest(token, him_token):
        return "him"
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"error": "unauthorized"})

# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(content={"error": exc.detail.get("error", "unauthorized")}, status_code=exc.status_code)

@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    return JSONResponse(content={"error": "unauthorized"}, status_code=status.HTTP_401_UNAUTHORIZED)

# Routes
@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/api/board")
async def board_endpoint(caller: str = Depends(get_caller), db = Depends(get_db)):
    today = date.today()
    board = household_board(db, today)
    return JSONResponse(content=board, status_code=status.HTTP_200_OK)

@app.post("/api/tickets")
async def create_ticket_endpoint(request: Request, caller: str = Depends(get_caller), db = Depends(get_db)):
    try:
        data = await request.json()
    except Exception:
        return JSONResponse(content={"error": "invalid request"}, status_code=status.HTTP_400_BAD_REQUEST)
    
    if not isinstance(data, dict):
        return JSONResponse(content={"error": "invalid request"}, status_code=status.HTTP_400_BAD_REQUEST)
    
    try:
        ticket = create_ticket(db, caller, data)
        return JSONResponse(content=ticket, status_code=status.HTTP_201_CREATED)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": "invalid request"})

@app.post("/api/tickets/{ticket_id}/status")
async def change_status_endpoint(ticket_id: int, request: Request, caller: str = Depends(get_caller), db = Depends(get_db)):
    try:
        data = await request.json()
    except Exception:
        return JSONResponse(content={"error": "invalid request"}, status_code=status.HTTP_400_BAD_REQUEST)
    
    if not isinstance(data, dict) or "status" not in data:
        return JSONResponse(content={"error": "invalid request"}, status_code=status.HTTP_400_BAD_REQUEST)

    if not isinstance(data["status"], str):
        return JSONResponse(content={"error": "invalid request"}, status_code=status.HTTP_400_BAD_REQUEST)
    
    try:
        updated = change_status(db, ticket_id, caller, data["status"])
        return JSONResponse(content=updated, status_code=status.HTTP_200_OK)
    except LookupError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "not found"})
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"error": "forbidden"})
    except ValueError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"error": "invalid transition"})

@app.get("/api/dashboard")
async def dashboard_endpoint(caller: str = Depends(get_caller), db = Depends(get_db)):
    today = date.today()
    dash = dashboard(db, caller, today)
    return JSONResponse(content=dash, status_code=status.HTTP_200_OK)

@app.get("/api/filed")
async def filed_endpoint(caller: str = Depends(get_caller), db = Depends(get_db)):
    tickets = filed(db, caller)
    return JSONResponse(content={"tickets": tickets}, status_code=status.HTTP_200_OK)

# Unknown path handler
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def catch_all(path: str):
    if path.startswith("api"):
        return JSONResponse(content={"error": "not found"}, status_code=status.HTTP_404_NOT_FOUND)
    return JSONResponse(content={"error": "method not allowed"}, status_code=status.HTTP_405_METHOD_NOT_ALLOWED)

# Initialize database on startup
@app.on_event("startup")
async def startup_db_client():
    init_db()