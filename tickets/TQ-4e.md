id: TQ-4e
unit: TQ-4
state: in review
depends_on: -
done_when: frontend/src/api.ts adds editTicket(token, id, changes), which sends PATCH /api/tickets/<id> with the changes as JSON and the bearer token and returns the parsed ticket, and fetchSummary(token), which GETs /api/summary; fetchBoard(token, filter?) sends only the non-empty fields of the optional filter (q, priority, assigned_to) as query parameters, and with no filter or an all-empty one GETs plain /api/board as before; both new calls throw new Error(String(status)) on an answer that is not ok, like the existing ones

# TQ-4e
