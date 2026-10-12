id: GQ-1f
unit: GQ-1
state: open
depends_on: GQ-1e
done_when: main.py adds POST /api/tickets, which passes the JSON body to rules.create_ticket with the caller as filer and answers 201 with the new ticket; main.py adds POST /api/tickets/{id}/status with the body {"status": <new status>}, which calls rules.change_status and answers 200 with the ticket, 404 {"error": "not found"} on LookupError, 403 {"error": "forbidden"} on PermissionError and 409 {"error": "invalid transition"} on ValueError; both routes need the caller (get_caller), so without a valid token they answer 401 {"error": "unauthorized"}; a body that is not valid JSON or not a JSON object, a create_ticket ValueError, a status body that is not exactly {"status": <a string>}, and a non-integer id are answered 400 with {"error": "invalid request"} — FastAPI's default 422 is replaced (a RequestValidationError handler), so the input is never echoed and no response carries a stack trace (read the body yourself with await request.json() inside a try); a request whose body is over 65536 bytes is answered 413 with {"error": "too large"} (checked in the middleware from the Content-Length header before the body is read) — a body of exactly 65536 bytes is read as usual

# GQ-1f
