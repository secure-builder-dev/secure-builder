import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import type { BoardFilter, TicketEdit, Summary } from "../src/types";
import * as api from "../src/api";

describe("api.ts E4 functions", () => {
  let originalFetch: typeof global.fetch;
  let mockResponse: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    originalFetch = global.fetch;
    mockResponse = vi.fn();
    global.fetch = mockResponse as unknown as typeof fetch;
  });

  afterEach(() => {
    global.fetch = originalFetch;
    vi.clearAllMocks();
  });

  describe("editTicket", () => {
    it("sends PATCH /api/tickets/<id> with changes as JSON and bearer token", async () => {
      const ticket = { id: 1, title: "Test", details: "", priority: "normal" as const, due: null, status: "open" as const, filed_by: "her" as const, assigned_to: "him" as const, created_at: "2024-01-01T00:00:00Z", updated_at: "2024-01-01T00:00:00Z" };
      mockResponse.mockResolvedValueOnce({
        ok: true,
        json: async () => ticket,
      });

      const changes: TicketEdit = { title: "Updated", details: "More info", priority: "urgent", due: "2024-12-31" };
      const result = await api.editTicket("test-token", 42, changes);

      expect(mockResponse).toHaveBeenCalledWith(
        "/api/tickets/42",
        expect.objectContaining({
          method: "PATCH",
          headers: expect.objectContaining({
            Authorization: "Bearer test-token",
            "Content-Type": "application/json",
          }),
          body: JSON.stringify(changes),
        })
      );
      expect(result).toEqual(ticket);
    });


    it("returns the parsed ticket", async () => {
      const ticket = { id: 1, title: "Test", details: "", priority: "normal" as const, due: null, status: "open" as const, filed_by: "her" as const, assigned_to: "him" as const, created_at: "2024-01-01T00:00:00Z", updated_at: "2024-01-01T00:00:00Z" };
      mockResponse.mockResolvedValueOnce({
        ok: true,
        json: async () => ticket,
      });

      const changes: TicketEdit = { title: "New Title", details: "", priority: "normal", due: null };
      const result = await api.editTicket("token", 1, changes);
      expect(result).toEqual(ticket);
    });

    it("throws new Error(String(status)) on non-ok response", async () => {
      mockResponse.mockResolvedValueOnce({
        ok: false,
        status: 403,
      });

      const changes: TicketEdit = { title: "X", details: "", priority: "normal", due: null };
      await expect(api.editTicket("token", 1, changes)).rejects.toThrowError("403");
    });

    it("throws on 404 not found", async () => {
      mockResponse.mockResolvedValueOnce({ ok: false, status: 404 });
      const changes: TicketEdit = { title: "X", details: "", priority: "normal", due: null };
      await expect(api.editTicket("token", 999, changes)).rejects.toThrowError("404");
    });

    it("throws on 400 invalid request", async () => {
      mockResponse.mockResolvedValueOnce({ ok: false, status: 400 });
      const changes: TicketEdit = { title: "X", details: "", priority: "normal", due: null };
      await expect(api.editTicket("token", 1, changes)).rejects.toThrowError("400");
    });

    it("throws on 409 not editable", async () => {
      mockResponse.mockResolvedValueOnce({ ok: false, status: 409 });
      const changes: TicketEdit = { title: "X", details: "", priority: "normal", due: null };
      await expect(api.editTicket("token", 1, changes)).rejects.toThrowError("409");
    });
  });

  describe("fetchSummary", () => {
    it("GETs /api/summary with bearer token", async () => {
      const summary: Summary = { overdue: 1, due_today: 2, open: 5 };
      mockResponse.mockResolvedValueOnce({
        ok: true,
        json: async () => summary,
      });

      const result = await api.fetchSummary("my-token");

      expect(mockResponse).toHaveBeenCalledWith(
        "/api/summary",
        expect.objectContaining({
          method: "GET",
          headers: expect.objectContaining({ Authorization: "Bearer my-token" }),
        })
      );
      expect(result).toEqual(summary);
    });

    it("returns the parsed summary", async () => {
      const summary: Summary = { overdue: 0, due_today: 0, open: 3 };
      mockResponse.mockResolvedValueOnce({ ok: true, json: async () => summary });
      const result = await api.fetchSummary("t");
      expect(result).toEqual(summary);
    });

    it("throws new Error(String(status)) on non-ok response", async () => {
      mockResponse.mockResolvedValueOnce({ ok: false, status: 500 });
      await expect(api.fetchSummary("token")).rejects.toThrowError("500");
    });

    it("throws on 401 unauthorized", async () => {
      mockResponse.mockResolvedValueOnce({ ok: false, status: 401 });
      await expect(api.fetchSummary("bad-token")).rejects.toThrowError("401");
    });
  });

  describe("fetchBoard with filter", () => {
    it("GETs plain /api/board when no filter is provided", async () => {
      const board = { todo: [], in_progress: [], completed: [] };
      mockResponse.mockResolvedValueOnce({ ok: true, json: async () => board });

      await api.fetchBoard("token" as any);

      expect(mockResponse).toHaveBeenCalledWith(
        "/api/board",
        expect.objectContaining({ method: "GET" })
      );
    });

    it("GETs plain /api/board when filter is all empty", async () => {
      const board = { todo: [], in_progress: [], completed: [] };
      mockResponse.mockResolvedValueOnce({ ok: true, json: async () => board });

      const filter: BoardFilter = { q: "", priority: "", assigned_to: "" };
      await api.fetchBoard("token", filter);

      expect(mockResponse).toHaveBeenCalledWith(
        "/api/board",
        expect.objectContaining({ method: "GET" })
      );
    });

    it("sends only non-empty q as query parameter", async () => {
      const board = { todo: [], in_progress: [], completed: [] };
      mockResponse.mockResolvedValueOnce({ ok: true, json: async () => board });

      const filter: BoardFilter = { q: "search term", priority: "", assigned_to: "" };
      await api.fetchBoard("token", filter);

      expect(mockResponse).toHaveBeenCalledWith(
        "/api/board?q=search+term",
        expect.any(Object)
      );
    });

    it("sends only non-empty priority as query parameter", async () => {
      const board = { todo: [], in_progress: [], completed: [] };
      mockResponse.mockResolvedValueOnce({ ok: true, json: async () => board });

      const filter: BoardFilter = { q: "", priority: "urgent", assigned_to: "" };
      await api.fetchBoard("token", filter);

      expect(mockResponse).toHaveBeenCalledWith(
        "/api/board?priority=urgent",
        expect.any(Object)
      );
    });

    it("sends only non-empty assigned_to as query parameter", async () => {
      const board = { todo: [], in_progress: [], completed: [] };
      mockResponse.mockResolvedValueOnce({ ok: true, json: async () => board });

      const filter: BoardFilter = { q: "", priority: "", assigned_to: "her" };
      await api.fetchBoard("token", filter);

      expect(mockResponse).toHaveBeenCalledWith(
        "/api/board?assigned_to=her",
        expect.any(Object)
      );
    });

    it("sends multiple non-empty fields as query parameters", async () => {
      const board = { todo: [], in_progress: [], completed: [] };
      mockResponse.mockResolvedValueOnce({ ok: true, json: async () => board });

      const filter: BoardFilter = { q: "fix", priority: "urgent", assigned_to: "him" };
      await api.fetchBoard("token", filter);

      // Order may vary; check that all params are present
      const callArgs = mockResponse.mock.calls[0][0];
      expect(callArgs).toContain("q=fix");
      expect(callArgs).toContain("priority=urgent");
      expect(callArgs).toContain("assigned_to=him");
    });

    it("throws new Error(String(status)) on non-ok response", async () => {
      mockResponse.mockResolvedValueOnce({ ok: false, status: 400 });
      const filter: BoardFilter = { q: "x", priority: "", assigned_to: "" };
      await expect(api.fetchBoard("token", filter)).rejects.toThrowError("400");
    });

    it("throws on 401 unauthorized", async () => {
      mockResponse.mockResolvedValueOnce({ ok: false, status: 401 });
      await expect(api.fetchBoard("bad-token" as any)).rejects.toThrowError("401");
    });
  });
});
