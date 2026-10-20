// GD-1g: frontend/src/api.ts — every fetch call of the personal board.
import "@testing-library/jest-dom/vitest";
import { describe, expect, it } from "vitest";
import { changeStatus, createTicket, fetchDashboard, fetchFiled } from "../src/api";
import { board, mockApi, ticket } from "./helpers";

describe("api.ts", () => {
  it("fetchDashboard sends GET /api/dashboard with the bearer token and returns the board", async () => {
    const b = board({ todo: [ticket({ title: "A" })] });
    const api = mockApi({ "GET /api/dashboard": { body: b } });
    await expect(fetchDashboard("tok-1")).resolves.toEqual(b);
    const [c] = api.calls("GET /api/dashboard");
    expect(c.headers["authorization"]).toBe("Bearer tok-1");
  });

  it("fetchFiled sends GET /api/filed with the bearer token and returns {tickets}", async () => {
    const body = { tickets: [ticket({ title: "F" })] };
    const api = mockApi({ "GET /api/filed": { body } });
    await expect(fetchFiled("tok-2")).resolves.toEqual(body);
    expect(api.calls("GET /api/filed")[0].headers["authorization"]).toBe("Bearer tok-2");
  });

  it("createTicket POSTs the ticket as JSON to /api/tickets and returns the new ticket", async () => {
    const made = ticket({ title: "New" });
    const api = mockApi({ "POST /api/tickets": { status: 201, body: made } });
    const data = { title: "New", details: "d", priority: "urgent" as const, due: "2026-10-20" };
    await expect(createTicket("tok-3", data)).resolves.toEqual(made);
    const [c] = api.calls("POST /api/tickets");
    expect(c.headers["authorization"]).toBe("Bearer tok-3");
    expect(c.headers["content-type"]).toContain("application/json");
    expect(c.body).toEqual(data);
  });

  it("changeStatus POSTs {status} to /api/tickets/{id}/status and returns the ticket", async () => {
    const moved = ticket({ id: 7, status: "acknowledged" });
    const api = mockApi({ "POST /api/tickets/:id/status": { body: moved } });
    await expect(changeStatus("tok-4", 7, "acknowledged")).resolves.toEqual(moved);
    const [c] = api.calls("POST /api/tickets/:id/status");
    expect(c.path).toBe("/api/tickets/7/status");
    expect(c.headers["authorization"]).toBe("Bearer tok-4");
    expect(c.headers["content-type"]).toContain("application/json");
    expect(c.body).toEqual({ status: "acknowledged" });
  });

  it("every call throws Error(status) on a non-ok answer", async () => {
    mockApi({
      "GET /api/dashboard": { status: 401, body: { error: "unauthorized" } },
      "GET /api/filed": { status: 500, body: { error: "x" } },
      "POST /api/tickets": { status: 400, body: { error: "invalid request" } },
      "POST /api/tickets/:id/status": { status: 409, body: { error: "invalid transition" } },
    });
    await expect(fetchDashboard("t")).rejects.toThrow(new Error("401"));
    await expect(fetchFiled("t")).rejects.toThrow(new Error("500"));
    await expect(createTicket("t", { title: "x", details: "", priority: "normal", due: null })).rejects.toThrow(new Error("400"));
    await expect(changeStatus("t", 1, "done")).rejects.toThrow(new Error("409"));
  });
});
