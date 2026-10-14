import "@testing-library/jest-dom/vitest";
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch as unknown as typeof fetch;

describe("api.ts", () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // Clause 1: exports exist and call correct endpoints
  it("exports fetchDashboard, fetchFiled, createTicket, and changeStatus", async () => {
    const api = await import("../src/api");
    expect(api.fetchDashboard).toBeInstanceOf(Function);
    expect(api.fetchFiled).toBeInstanceOf(Function);
    expect(api.createTicket).toBeInstanceOf(Function);
    expect(api.changeStatus).toBeInstanceOf(Function);
  });

  it("fetchDashboard calls GET /api/dashboard", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ todo: [], in_progress: [], completed: [] }),
    });
    const api = await import("../src/api");
    await api.fetchDashboard("test-token");
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/dashboard"),
      expect.objectContaining({ method: "GET" })
    );
  });

  it("fetchFiled calls GET /api/filed", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ tickets: [] }),
    });
    const api = await import("../src/api");
    await api.fetchFiled("test-token");
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/filed"),
      expect.objectContaining({ method: "GET" })
    );
  });

  it("createTicket calls POST /api/tickets with JSON body", async () => {
    const data = { title: "Test", details: "", priority: "normal" as const, due: null };
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ id: 1, ...data, status: "open", filed_by: "her", assigned_to: "him", created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" }),
    });
    const api = await import("../src/api");
    await api.createTicket("test-token", data);
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/tickets"),
      expect.objectContaining({ method: "POST" })
    );
  });

  it("changeStatus calls POST /api/tickets/{id}/status with JSON body", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ id: 1, title: "Test", details: "", priority: "normal" as const, due: null, status: "acknowledged", filed_by: "her", assigned_to: "him", created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" }),
    });
    const api = await import("../src/api");
    await api.changeStatus("test-token", 1, "acknowledged" as const);
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/tickets/1/status"),
      expect.objectContaining({ method: "POST" })
    );
  });

  // Clause 2: Authorization header and Content-Type for body calls
  it("every call sends Authorization: Bearer <token>", async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({ todo: [], in_progress: [], completed: [] }) });
    const api = await import("../src/api");
    await api.fetchDashboard("my-token");
    expect(mockFetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({ headers: expect.objectContaining({ Authorization: "Bearer my-token" }) })
    );
  });

  it("createTicket sends Content-Type: application/json", async () => {
    const data = { title: "Test", details: "", priority: "normal" as const, due: null };
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ id: 1, ...data, status: "open", filed_by: "her", assigned_to: "him", created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" }),
    });
    const api = await import("../src/api");
    await api.createTicket("test-token", data);
    expect(mockFetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({ headers: expect.objectContaining({ "Content-Type": "application/json" }) })
    );
  });

  it("changeStatus sends Content-Type: application/json", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ id: 1, title: "Test", details: "", priority: "normal" as const, due: null, status: "acknowledged", filed_by: "her", assigned_to: "him", created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" }),
    });
    const api = await import("../src/api");
    await api.changeStatus("test-token", 1, "acknowledged" as const);
    expect(mockFetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({ headers: expect.objectContaining({ "Content-Type": "application/json" }) })
    );
  });

  it("returns parsed JSON of an ok answer", async () => {
    const board = { todo: [], in_progress: [], completed: [] };
    mockFetch.mockResolvedValueOnce({ ok: true, json: async () => board });
    const api = await import("../src/api");
    const result = await api.fetchDashboard("test-token");
    expect(result).toEqual(board);
  });

  // Clause 3: throws Error(String(status)) on non-ok
  it("throws Error('401') on 401 response", async () => {
    mockFetch.mockResolvedValueOnce({ ok: false, status: 401 });
    const api = await import("../src/api");
    await expect(api.fetchDashboard("bad-token")).rejects.toThrow(new Error("401"));
  });

  it("throws Error('404') on 404 response", async () => {
    mockFetch.mockResolvedValueOnce({ ok: false, status: 404 });
    const api = await import("../src/api");
    await expect(api.fetchDashboard("test-token")).rejects.toThrow(new Error("404"));
  });

  it("throws Error('500') on 500 response", async () => {
    mockFetch.mockResolvedValueOnce({ ok: false, status: 500 });
    const api = await import("../src/api");
    await expect(api.fetchDashboard("test-token")).rejects.toThrow(new Error("500"));
  });

  it("throws Error(String(status)) for createTicket on non-ok", async () => {
    mockFetch.mockResolvedValueOnce({ ok: false, status: 400 });
    const api = await import("../src/api");
    const data = { title: "Test", details: "", priority: "normal" as const, due: null };
    await expect(api.createTicket("test-token", data)).rejects.toThrow(new Error("400"));
  });

  it("throws Error(String(status)) for changeStatus on non-ok", async () => {
    mockFetch.mockResolvedValueOnce({ ok: false, status: 403 });
    const api = await import("../src/api");
    await expect(api.changeStatus("test-token", 1, "invalid" as any)).rejects.toThrow(new Error("403"));
  });
});
