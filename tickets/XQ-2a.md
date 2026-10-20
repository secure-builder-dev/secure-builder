id: XQ-2a
unit: XQ-2
state: in review
depends_on: -
done_when: frontend/src/api.ts exports fetchDashboard(token) (GET /api/dashboard, returns a Board), fetchFiled(token) (GET /api/filed, returns {tickets}), createTicket(token, data) (POST /api/tickets with the NewTicket as JSON, returns the Ticket) and changeStatus(token, id, status) (POST /api/tickets/{id}/status with {status} as JSON, returns the Ticket), using the types of frontend/src/types.ts; every call sends the header Authorization: Bearer <token>, a call with a body also sends Content-Type: application/json, and every call returns the parsed JSON of an ok answer; on an answer that is not ok every call throws new Error(String(status)), so a 401 throws Error('401')

# XQ-2a
