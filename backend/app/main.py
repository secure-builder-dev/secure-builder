import os
import hmac
from datetime import datetime, timezone
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session

from app.db import SessionLocal, init_db
from app.rules import dashboard, filed, create_ticket, change_status

app = FastAPI()


@app.on_event("startup")
def startup():
    init_db()


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = "default-src 'none'"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_caller(request: Request) -> str:
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer ") or not auth[7:]:
        raise HTTPException(status_code=401, detail={"error": "unauthorized"})
    
    token = auth[7:]
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
        status_code=exc.status_code,
        content={"error": exc.detail.get("error", "not found")}
    )

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=404, content={"error": "not found"})

@app.exception_handler(405)
async def method_not_allowed_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=405, content={"error": "method not allowed"})

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={"error": "invalid request"}
    )

@app.middleware("http")
async def check_body_size(request: Request, call_next):
    content_length = request.headers.get("Content-Length")
    if content_length and int(content_length) > 65536:
        return JSONResponse(
            status_code=413,
            content={"error": "too large"}
        )
    return await call_next(request)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/dashboard")
def api_dashboard(caller: str = Depends(get_caller), db: Session = Depends(get_db)):
    today = datetime.now(timezone.utc).date()
    return dashboard(db, caller, today)


@app.get("/api/filed")
def api_filed(caller: str = Depends(get_caller), db: Session = Depends(get_db)):
    return {"tickets": filed(db, caller)}


@app.get("/api/board")
def api_board(caller: str = Depends(get_caller), db: Session = Depends(get_db)):
    today = datetime.now(timezone.utc).date()
    from app.household import household_board
    return household_board(db, today)


@app.get("/api/me")
def api_me(caller: str = Depends(get_caller)):
    return {"user": caller}


@app.post("/api/tickets")
async def api_create_ticket(request: Request, caller: str = Depends(get_caller), db: Session = Depends(get_db)):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail={"error": "invalid request"})
    
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail={"error": "invalid request"})
    
    try:
        ticket = create_ticket(db, caller, body)
    except ValueError:
        raise HTTPException(status_code=400, detail={"error": "invalid request"})
    
    return JSONResponse(status_code=201, content=ticket)


@app.post("/api/tickets/{ticket_id}/status")
async def api_change_status(request: Request, ticket_id: int, caller: str = Depends(get_caller), db: Session = Depends(get_db)):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail={"error": "invalid request"})
    
    if not isinstance(body, dict) or body.keys() != {"status"} or not isinstance(body["status"], str):
        raise HTTPException(status_code=400, detail={"error": "invalid request"})
    
    try:
        ticket = change_status(db, ticket_id, caller, body["status"])
    except LookupError:
        raise HTTPException(status_code=404, detail={"error": "not found"})
    except PermissionError:
        raise HTTPException(status_code=403, detail={"error": "forbidden"})
    except ValueError:
        raise HTTPException(status_code=409, detail={"error": "invalid transition"})
    
    return JSONResponse(status_code=200, content=ticket)
