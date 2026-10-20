import datetime as dt
import hmac
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import db, rules


@asynccontextmanager
async def lifespan(app):
    db.init_db()
    yield


app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = "default-src 'none'"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


def get_db():
    session = db.SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_caller(request: Request):
    header = request.headers.get("Authorization")
    if not header or not header.startswith("Bearer "):
        raise StarletteHTTPException(status_code=401, detail="unauthorized")
    token = header[len("Bearer "):]
    if not token:
        raise StarletteHTTPException(status_code=401, detail="unauthorized")
    for name, user in (("TOKEN_HER", "her"), ("TOKEN_HIM", "him")):
        expected = os.environ.get(name)
        if expected and hmac.compare_digest(token.encode("utf-8"), expected.encode("utf-8")):
            return user
    raise StarletteHTTPException(status_code=401, detail="unauthorized")


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return JSONResponse(status_code=404, content={"error": "not found"})
    if exc.status_code == 405:
        return JSONResponse(status_code=405, content={"error": "method not allowed"})
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/dashboard")
def dashboard(session=Depends(get_db), caller=Depends(get_caller)):
    today = dt.datetime.now(dt.timezone.utc).date()
    return rules.dashboard(session, caller, today)


@app.get("/api/filed")
def filed(session=Depends(get_db), caller=Depends(get_caller)):
    return {"tickets": rules.filed(session, caller)}
