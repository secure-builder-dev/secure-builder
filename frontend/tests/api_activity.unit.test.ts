// TO-3e: frontend/src/api.ts — fetchTicket, fetchComments, fetchHistory and addComment.
import "@testing-library/jest-dom/vitest";
import { afterEach, describe, expect, it, vi } from "vitest";
import { addComment, fetchComments, fetchHistory, fetchTicket } from "../src/api";
import { comment, event, mockApi, ticket } from "./helpers";

afterEach(() => { vi.restoreAllMocks(); });

describe("api.ts: comments and history", () => {
  it("fetchTicket sends GET /api/tickets/<id> with the bearer token and returns the ticket", async () => {
    const t = ticket({ id: 12, title: "Fix the sink" });
    const api = mockApi({ "GET /api/tickets/:id": { body: t } });
    await expect(fetchTicket("tok-t", 12)).resolves.toEqual(t);
    const calls = api.calls("GET /api/tickets/:id");
    expect(calls).toHaveLength(1);
    expect(calls[0].path).toBe("/api/tickets/12");
    expect(calls[0].headers["authorization"]).toBe("Bearer tok-t");
  });

  it("fetchComments sends GET /api/tickets/<id>/comments with the bearer token and returns {comments}", async () => {
    const body = { comments: [comment({ ticket_id: 7, body: "first" }), comment({ ticket_id: 7, body: "second" })] };
    const api = mockApi({ "GET /api/tickets/:id/comments": { body } });
    await expect(fetchComments("tok-c", 7)).resolves.toEqual(body);
    const calls = api.calls("GET /api/tickets/:id/comments");
    expect(calls).toHaveLength(1);
    expect(calls[0].path).toBe("/api/tickets/7/comments");
    expect(calls[0].headers["authorization"]).toBe("Bearer tok-c");
  });

  it("fetchHistory sends GET /api/tickets/<id>/history with the bearer token and returns {events}", async () => {
    const body = { events: [event({ ticket_id: 9 }), event({ ticket_id: 9, kind: "status", from_status: "open", to_status: "acknowledged" })] };
    const api = mockApi({ "GET /api/tickets/:id/history": { body } });
    await expect(fetchHistory("tok-h", 9)).resolves.toEqual(body);
    const calls = api.calls("GET /api/tickets/:id/history");
    expect(calls).toHaveLength(1);
    expect(calls[0].path).toBe("/api/tickets/9/history");
    expect(calls[0].headers["authorization"]).toBe("Bearer tok-h");
  });

  it("addComment POSTs {body} as JSON to /api/tickets/<id>/comments and returns the comment", async () => {
    const made = comment({ ticket_id: 5, author: "him", body: "On it" });
    const api = mockApi({ "POST /api/tickets/:id/comments": { status: 201, body: made } });
    await expect(addComment("tok-a", 5, "On it")).resolves.toEqual(made);
    const calls = api.calls("POST /api/tickets/:id/comments");
    expect(calls).toHaveLength(1);
    expect(calls[0].path).toBe("/api/tickets/5/comments");
    expect(calls[0].headers["authorization"]).toBe("Bearer tok-a");
    expect(calls[0].headers["content-type"]).toContain("application/json");
    expect(calls[0].body).toEqual({ body: "On it" });
  });

  it("each new call throws Error(status) on a non-ok answer", async () => {
    mockApi({
      "GET /api/tickets/:id": { status: 404, body: { error: "not found" } },
      "GET /api/tickets/:id/comments": { status: 401, body: { error: "unauthorized" } },
      "GET /api/tickets/:id/history": { status: 500, body: { error: "x" } },
      "POST /api/tickets/:id/comments": { status: 400, body: { error: "invalid request" } },
    });
    await expect(fetchTicket("t", 1)).rejects.toThrow(new Error("404"));
    await expect(fetchComments("t", 1)).rejects.toThrow(new Error("401"));
    await expect(fetchHistory("t", 1)).rejects.toThrow(new Error("500"));
    await expect(addComment("t", 1, "x")).rejects.toThrow(new Error("400"));
  });
});
