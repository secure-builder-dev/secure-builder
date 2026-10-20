id: XO-3e
unit: XO-3
state: in review
depends_on: -
done_when: frontend/src/api.ts adds fetchTicket(token, id), fetchComments(token, id) and fetchHistory(token, id), which GET /api/tickets/<id>, /api/tickets/<id>/comments and /api/tickets/<id>/history with the bearer token and return the parsed JSON; addComment(token, id, body) POSTs {"body": body} as JSON to /api/tickets/<id>/comments with the bearer token and returns the parsed comment; each of them throws new Error(String(status)) on an answer that is not ok, like the existing calls, which stay as they are

# XO-3e
