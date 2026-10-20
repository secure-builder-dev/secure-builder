// TO-4e: frontend/src/api.ts — editTicket, fetchSummary and the filter argument of fetchBoard.
import "@testing-library/jest-dom/vitest";
import { afterEach, describe, expect, it, vi } from "vitest";
import { editTicket, fetchBoard, fetchSummary } from "../src/api";
import type { BoardFilter, TicketEdit } from "../src/types";
import { board, mockApi, ticket } from "./helpers";

afterEach(() => { vi.restoreAllMocks(); });

function requestedUrl(api: ReturnType<typeof mockApi>, i = 0): string {
  const input = api.fn.mock.calls[i][0] as unknown;
  return typeof input === "string" ? input : input instanceof URL ? input.href : (input as Request).url;
}

describe("editTicket", () => {
  it("sends PATCH /api/tickets/<id> with the changes as JSON and the bearer token, and returns the ticket", async () => {
    const edited = ticket({ id: 21, title: "Paint the fence" });
    const api = mockApi({ "PATCH /api/tickets/:id": { body: edited } });
    const changes: TicketEdit = { title: "Paint the fence", details: "white", priority: "urgent", due: "2026-11-02" };
    await expect(editTicket("tok-e", 21, changes)).resolves.toEqual(edited);
    const calls = api.calls("PATCH /api/tickets/:id");
    expect(calls).toHaveLength(1);
    expect(calls[0].path).toBe("/api/tickets/21");
    expect(calls[0].headers["authorization"]).toBe("Bearer tok-e");
    expect(calls[0].headers["content-type"]).toContain("application/json");
    expect(calls[0].body).toEqual(changes);
  });

  it("sends a null due as null", async () => {
    const api = mockApi({ "PATCH /api/tickets/:id": { body: ticket({ id: 3 }) } });
    await editTicket("t", 3, { title: "A", details: "", priority: "low", due: null });
    expect(api.calls("PATCH /api/tickets/:id")[0].body).toEqual({ title: "A", details: "", priority: "low", due: null });
  });

  it("throws Error(status) on a non-ok answer", async () => {
    mockApi({ "PATCH /api/tickets/:id": { status: 409, body: { error: "not editable" } } });
    await expect(editTicket("t", 1, { title: "x", details: "", priority: "normal", due: null })).rejects.toThrow(new Error("409"));
  });
});

describe("fetchSummary", () => {
  it("sends GET /api/summary with the bearer token and returns the summary", async () => {
    const s = { overdue: 2, due_today: 1, open: 5 };
    const api = mockApi({ "GET /api/summary": { body: s } });
    await expect(fetchSummary("tok-s")).resolves.toEqual(s);
    const calls = api.calls("GET /api/summary");
    expect(calls).toHaveLength(1);
    expect(calls[0].headers["authorization"]).toBe("Bearer tok-s");
  });

  it("throws Error(status) on a non-ok answer", async () => {
    mockApi({ "GET /api/summary": { status: 401, body: { error: "unauthorized" } } });
    await expect(fetchSummary("t")).rejects.toThrow(new Error("401"));
  });
});

describe("fetchBoard with a filter", () => {
  it("with no filter GETs plain /api/board with the bearer token", async () => {
    const b = board({ todo: [ticket({ title: "A" })] });
    const api = mockApi({ "GET /api/board": { body: b } });
    await expect(fetchBoard("tok-b")).resolves.toEqual(b);
    const [c] = api.calls("GET /api/board");
    expect(c.query).toEqual({});
    expect(c.headers["authorization"]).toBe("Bearer tok-b");
    expect(requestedUrl(api)).not.toContain("?");
  });

  it("with an all-empty filter GETs plain /api/board", async () => {
    const api = mockApi();
    const f: BoardFilter = { q: "", priority: "", assigned_to: "" };
    await fetchBoard("t", f);
    expect(api.calls("GET /api/board")).toHaveLength(1);
    expect(api.calls("GET /api/board")[0].query).toEqual({});
    expect(requestedUrl(api)).not.toContain("?");
  });

  it("sends every non-empty field as a query parameter and returns the board", async () => {
    const b = board({ todo: [ticket({ title: "Match" })] });
    const api = mockApi({ "GET /api/board": { body: b } });
    const f: BoardFilter = { q: "sink", priority: "urgent", assigned_to: "him" };
    await expect(fetchBoard("tok-f", f)).resolves.toEqual(b);
    const [c] = api.calls("GET /api/board");
    expect(c.query).toEqual({ q: "sink", priority: "urgent", assigned_to: "him" });
    expect(c.headers["authorization"]).toBe("Bearer tok-f");
  });

  it("leaves the empty fields out", async () => {
    const api = mockApi();
    await fetchBoard("t", { q: "", priority: "low", assigned_to: "" });
    await fetchBoard("t", { q: "paint", priority: "", assigned_to: "" });
    await fetchBoard("t", { q: "", priority: "", assigned_to: "her" });
    expect(api.calls("GET /api/board").map((c) => c.query)).toEqual([
      { priority: "low" }, { q: "paint" }, { assigned_to: "her" },
    ]);
  });

  it("encodes the search text as a query value", async () => {
    const api = mockApi();
    await fetchBoard("t", { q: "a&b c=d", priority: "", assigned_to: "" });
    expect(api.calls("GET /api/board")[0].query).toEqual({ q: "a&b c=d" });
  });

  it("throws Error(status) on a non-ok answer with a filter", async () => {
    mockApi({ "GET /api/board": { status: 400, body: { error: "invalid request" } } });
    await expect(fetchBoard("t", { q: "x", priority: "", assigned_to: "" })).rejects.toThrow(new Error("400"));
  });
});
