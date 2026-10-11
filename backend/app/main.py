import os
import hmac
from datetime import date
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.db import SessionLocal, init_db
from app.rules import create_ticket, change_status, dashboard, filed

app = FastAPI()

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = "default-src 'none'"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response

@app.middleware("http")
async def validate_content_length(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > 65536:
        return JSONResponse(
            status_code=413,
            content={"error": "too large"}
        )
    return await call_next(request)

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": "internal server error"}
    )

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_caller(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="unauthorized")
    
    token = auth_header.split(" ", 1)[1]
    her_token = os.getenv("TOKEN_HER")
    him_token = os.getenv("TOKEN_HIM")
    
    if not her_token or not him_token:
        raise HTTPException(status_code=401, detail="unauthorized")
    
    if hmac.compare_digest(token, her_token):
        return "her"
    elif hmac.compare_digest(token, him_token):
        return "him"
    else:
        raise HTTPException(status_code=401, detail="unauthorized")

@app.on_event("startup")
async def startup():
    init_db()

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/api/tickets")
async def create_ticket_endpoint(
    request: Request,
    caller: str = Depends(get_caller),
    db: Session = Depends(get_db)
):
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="invalid request")
    
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="invalid request")
    
    try:
        ticket = create_ticket(db, caller, data)
        return JSONResponse(status_code=201, content=ticket)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="invalid request")

@app.post("/api/tickets/{ticket_id}/status")
async def change_status_endpoint(
    ticket_id: int,
    request: Request,
    caller: str = Depends(get_caller),
    db: Session = Depends(get_db)
):
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="invalid request")
    
    if not isinstance(data, dict) or "status" not in data:
        raise HTTPException(status_code=400, detail="invalid request")
    
    new_status = data["status"]
    
    try:
        updated_ticket = change_status(db, ticket_id, caller, new_status)
        return JSONResponse(status_code=200, content=updated_ticket)
    except LookupError:
        raise HTTPException(status_code=404, detail="not found")
    except PermissionError:
        raise HTTPException(status_code=403, detail="forbidden")
    except ValueError:
        raise HTTPException(status_code=409, detail="invalid transition")

@app.get("/api/dashboard")
async def dashboard_endpoint(
    caller: str = Depends(get_caller),
    db: Session = Depends(get_db)
):
    today = date.today()
    dash = dashboard(db, caller, today)
    return JSONResponse(status_code=200, content=dash)

@app.get("/api/filed")
async def filed_endpoint(
    caller: str = Depends(get_caller),
    db: Session = Depends(get_db)
):
    tickets = filed(db, caller)
    return JSONResponse(status_code=200, content={"tickets": tickets})

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def catch_all(path: str, request: Request):
    if request.method == "GET":
        raise HTTPException(status_code=404, detail="not found")
    else:
        raise HTTPException(status_code=405, detail="method not allowed")