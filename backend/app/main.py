import datetime as dt
import hmac
import json
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import activity, db, household, rules


@asynccontextmanager
async def lifespan(app):
    db.init_db()
    yield


app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def security_headers(request, call_next):
    length = request.headers.get("Content-Length")
    if length is not None and length.isdigit() and int(length) > 65536:
        return JSONResponse(status_code=413, content={"error": "too large"})
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


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=400, content={"error": "invalid request"})


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


@app.get("/api/board")
def board(session=Depends(get_db), caller=Depends(get_caller)):
    today = dt.datetime.now(dt.timezone.utc).date()
    return household.household_board(session, today)


@app.get("/api/me")
def me(caller=Depends(get_caller)):
    return {"user": caller}


async def _read_json_object(request: Request):
    try:
        data = await request.json()
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    return data


@app.post("/api/tickets", status_code=201)
async def create_ticket_route(request: Request, session=Depends(get_db), caller=Depends(get_caller)):
    data = await _read_json_object(request)
    if data is None:
        return JSONResponse(status_code=400, content={"error": "invalid request"})
    try:
        ticket = rules.create_ticket(session, caller, data)
    except ValueError:
        session.rollback()
        return JSONResponse(status_code=400, content={"error": "invalid request"})
    return JSONResponse(status_code=201, content=ticket)


@app.get("/api/tickets/{ticket_id}")
def get_ticket(ticket_id: int, session=Depends(get_db), caller=Depends(get_caller)):
    ticket = session.get(db.Base.registry.mappers[0].class_, ticket_id) if False else None
    from app.models import Ticket
    ticket = session.get(Ticket, ticket_id)
    if ticket is None:
        return JSONResponse(status_code=404, content={"error": "not found"})
    return rules.ticket_to_dict(ticket)


@app.get("/api/tickets/{ticket_id}/comments")
def list_comments_route(ticket_id: int, session=Depends(get_db), caller=Depends(get_caller)):
    try:
        comments = activity.list_comments(session, ticket_id, caller)
    except LookupError:
        return JSONResponse(status_code=404, content={"error": "not found"})
    return {"comments": comments}


@app.post("/api/tickets/{ticket_id}/comments", status_code=201)
async def add_comment_route(request: Request, ticket_id: int, session=Depends(get_db), caller=Depends(get_caller)):
    data = await _read_json_object(request)
    if data is None or set(data) != {"body"}:
        return JSONResponse(status_code=400, content={"error": "invalid request"})
    try:
        comment = activity.add_comment(session, ticket_id, caller, data["body"])
    except LookupError:
        session.rollback()
        return JSONResponse(status_code=404, content={"error": "not found"})
    except ValueError:
        session.rollback()
        return JSONResponse(status_code=400, content={"error": "invalid request"})
    return JSONResponse(status_code=201, content=comment)


@app.get("/api/tickets/{ticket_id}/history")
def history_route(ticket_id: int, session=Depends(get_db), caller=Depends(get_caller)):
    try:
        events = activity.ticket_history(session, ticket_id, caller)
    except LookupError:
        return JSONResponse(status_code=404, content={"error": "not found"})
    return {"events": events}


@app.post("/api/tickets/{ticket_id}/status")
async def change_status_route(request: Request, ticket_id: int, session=Depends(get_db), caller=Depends(get_caller)):
    data = await _read_json_object(request)
    if (
        data is None
        or set(data) != {"status"}
        or not isinstance(data["status"], str)
    ):
        return JSONResponse(status_code=400, content={"error": "invalid request"})
    try:
        ticket = rules.change_status(session, ticket_id, caller, data["status"])
    except LookupError:
        session.rollback()
        return JSONResponse(status_code=404, content={"error": "not found"})
    except PermissionError:
        session.rollback()
        return JSONResponse(status_code=403, content={"error": "forbidden"})
    except ValueError:
        session.rollback()
        return JSONResponse(status_code=409, content={"error": "invalid transition"})
    return ticket
