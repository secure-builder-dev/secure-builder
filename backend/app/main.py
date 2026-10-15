import os
import hmac
from datetime import datetime, timezone
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db import SessionLocal, init_db
from app.rules import dashboard, filed

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
