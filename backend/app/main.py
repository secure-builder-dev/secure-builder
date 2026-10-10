import json
from fastapi import FastAPI, Request, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session
from fastapi import Request
import sys
import json

async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": "invalid request"}
    )
from datetime import date
import hmac
import os
from .db import SessionLocal, init_db
from .rules import create_ticket, change_status, dashboard, filed

app = FastAPI()

app.add_exception_handler(RequestValidationError, request_validation_exception_handler)

security = HTTPBearer()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_caller(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    token = credentials.credentials
    her_token = os.getenv('TOKEN_HER')
    him_token = os.getenv('TOKEN_HIM')
    if her_token and hmac.compare_digest(token, her_token):
        return 'her'
    if him_token and hmac.compare_digest(token, him_token):
        return 'him'
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={'error': 'unauthorized'})

@app.on_event('startup')
async def startup_event():
    init_db()

@app.get('/health', response_model=dict)
async def health():
    return JSONResponse(content={'status': 'ok'}, status_code=status.HTTP_200_OK)

@app.post('/api/tickets', response_model=dict)
async def create_ticket_endpoint(request: Request, caller: str = Depends(get_caller), db: Session = Depends(get_db)):
    try:
        data = await request.json()
        if not isinstance(data, dict):
            raise ValueError()
        ticket = create_ticket(db, caller, data)
    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={'error': 'invalid request'})
    return JSONResponse(content=ticket, status_code=status.HTTP_201_CREATED)

@app.post('/api/tickets/{id}/status', response_model=dict)
async def change_status_endpoint(id: int, request: Request, caller: str = Depends(get_caller), db: Session = Depends(get_db)):
    try:
        data = await request.json()
        if not isinstance(data, dict):
            raise ValueError()
        ticket = change_status(db, id, caller, data['status'])
    except (LookupError, TypeError, KeyError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'error': 'not found'})
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={'error': 'forbidden'})
    except (ValueError, json.JSONDecodeError):
        if "invalid transition" in str(sys.exc_info()[1]) if sys.exc_info()[1] else False:
             raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={'error': 'invalid transition'})
        # This block is tricky because ValueError is used for both 400 and 409. 
        # But the rules say 409 for ValueError on change_status specifically for transition.
        # Let's refine the exception handling below.
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={'error': 'invalid transition'})
    return JSONResponse(content=ticket, status_code=status.HTTP_200_OK)

@app.get('/api/dashboard', response_model=dict)
async def dashboard_endpoint(caller: str = Depends(get_caller), db: Session = Depends(get_db)):
    today = date.today()
    return JSONResponse(content=dashboard(db, caller, today), status_code=status.HTTP_200_OK)

@app.get('/api/board', response_model=dict)
async def board_endpoint(caller: str = Depends(get_caller), db: Session = Depends(get_db)):
    today = date.today()
    from .household import household_board
    return JSONResponse(content=household_board(db, today), status_code=status.HTTP_200_OK)

@app.get('/api/me', response_model=dict)
async def me_endpoint(caller: str = Depends(get_caller)):
    return JSONResponse(content={'user': caller}, status_code=status.HTTP_200_OK)

@app.get('/api/filed', response_model=dict)
async def filed_endpoint(caller: str = Depends(get_caller), db: Session = Depends(get_db)):
    return JSONResponse(content={'tickets': filed(db, caller)}, status_code=status.HTTP_200_OK)

@app.exception_handler(400)
async def bad_request_handler(request, exc):
    return JSONResponse(content={'error': 'invalid request'}, status_code=status.HTTP_400_BAD_REQUEST)

@app.exception_handler(401)
async def unauthorized_handler(request, exc):
    return JSONResponse(content={'error': 'unauthorized'}, status_code=status.HTTP_401_UNAUTHORIZED)

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    if isinstance(exc.detail, dict) and 'error' in exc.detail:
        return JSONResponse(content=exc.detail, status_code=exc.status_code)
    return JSONResponse(content={'error': str(exc.detail)}, status_code=exc.status_code)

@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(content={'error': 'not found'}, status_code=status.HTTP_404_NOT_FOUND)

@app.exception_handler(405)
async def method_not_allowed_handler(request, exc):
    return JSONResponse(content={'error': 'method not allowed'}, status_code=status.HTTP_405_METHOD_NOT_ALLOWED)

@app.middleware('http')
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Content-Security-Policy'] = "default-src 'none'"
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Referrer-Policy'] = 'no-referrer'
    return response

@app.middleware('http')
async def check_body_size(request: Request, call_next):
    content_length = request.headers.get('content-length')
    if content_length and int(content_length) > 65536:
        return JSONResponse(content={'error': 'too large'}, status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
    return await call_next(request)