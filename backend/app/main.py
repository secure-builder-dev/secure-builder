import os
from datetime import datetime, timezone
from typing import Annotated

import hmac
from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db import SessionLocal, init_db

app = FastAPI()


@app.on_event("startup")
async def startup():
    init_db()


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
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = "default-src 'none'"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


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