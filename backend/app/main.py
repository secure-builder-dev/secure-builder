import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import hmac

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.db import SessionLocal, init_db
from app import rules


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)


async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_caller(request: Request) -> str:
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail={"error": "unauthorized"})
    token = auth.split(" ", 1)[1]
    if not token:
        raise HTTPException(status_code=401, detail={"error": "unauthorized"})

    her_token = os.environ.get("TOKEN_HER", "")
    him_token = os.environ.get("TOKEN_HIM", "")

    if hmac.compare_digest(token, her_token):
        return "her"
    if hmac.compare_digest(token, him_token):
        return "him"

    raise HTTPException(status_code=401, detail={"error": "unauthorized"})


@app.get("/health")
async def health():
    return JSONResponse(content={"status": "ok"})


@app.get("/api/dashboard")
async def dashboard(caller: str = Depends(get_caller), db=Depends(get_db)):
    today = datetime.now(timezone.utc).date()
    board = rules.dashboard(db, caller, today)
    return JSONResponse(content=board)


@app.get("/api/filed")
async def filed(caller: str = Depends(get_caller), db=Depends(get_db)):
    tickets = rules.filed(db, caller)
    return JSONResponse(content={"tickets": tickets})


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    error_map = {
        401: "unauthorized",
        404: "not found",
        405: "method not allowed",
    }
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": error_map.get(exc.status_code, "not found")},
    )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=404,
        content={"error": "not found"},
    )


@app.exception_handler(405)
async def method_not_allowed_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=405,
        content={"error": "method not allowed"},
    )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "default-src 'none'"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response


class BodySizeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("Content-Length")
        if content_length and int(content_length) > 65536:
            return JSONResponse(
                status_code=413,
                content={"error": "too large"},
            )
        return await call_next(request)


@app.exception_handler(Exception)
async def validation_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=400,
        content={"error": "invalid request"},
    )


@app.post("/api/tickets")
async def create_ticket_endpoint(caller: str = Depends(get_caller), db=Depends(get_db), request: Request = None):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "invalid request"})
    
    if not isinstance(body, dict):
        return JSONResponse(status_code=400, content={"error": "invalid request"})
    
    try:
        ticket = rules.create_ticket(db, caller, body)
        return JSONResponse(content=ticket, status_code=201)
    except ValueError:
        return JSONResponse(status_code=400, content={"error": "invalid request"})


@app.post("/api/tickets/{ticket_id}/status")
async def change_status_endpoint(ticket_id: str, caller: str = Depends(get_caller), db=Depends(get_db), request: Request = None):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "invalid request"})
    
    if not isinstance(body, dict) or body.keys() != {"status"} or not isinstance(body["status"], str):
        return JSONResponse(status_code=400, content={"error": "invalid request"})
    
    new_status = body["status"]
    
    try:
        ticket_id_int = int(ticket_id)
    except ValueError:
        return JSONResponse(status_code=400, content={"error": "invalid request"})
    
    try:
        ticket = rules.change_status(db, ticket_id_int, caller, new_status)
        return JSONResponse(content=ticket)
    except LookupError:
        return JSONResponse(status_code=404, content={"error": "not found"})
    except PermissionError:
        return JSONResponse(status_code=403, content={"error": "forbidden"})
    except ValueError:
        return JSONResponse(status_code=409, content={"error": "invalid transition"})


app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(BodySizeMiddleware)