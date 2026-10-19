// Unit tests for the new API activity functions (fetchTicket, fetchComments, fetchHistory, addComment)
import { afterEach, beforeEach, expect, test, vi, describe } from "vitest";
import * as api from "../src/api";

describe("API activity functions", () => {
  const token = "TOKEN";

  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  test("fetchTicket performs GET and returns parsed JSON", async () => {
    const mockData = { id: 1, title: "Test" };
    (global.fetch as any).mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => mockData,
    });
    const result = await (api as any).fetchTicket(token, 1);
    expect(global.fetch).toHaveBeenCalledWith("/api/tickets/1", {
      method: "GET",
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(result).toEqual(mockData);
  });

  test("fetchTicket throws on non‑ok response", async () => {
    (global.fetch as any).mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => ({}),
    });
    await expect((api as any).fetchTicket(token, 1)).rejects.toThrow("404");
  });

  test("fetchComments performs GET and returns parsed JSON", async () => {
    const mockData = { comments: [] };
    (global.fetch as any).mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => mockData,
    });
    const result = await (api as any).fetchComments(token, 2);
    expect(global.fetch).toHaveBeenCalledWith("/api/tickets/2/comments", {
      method: "GET",
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(result).toEqual(mockData);
  });

  test("fetchComments throws on non‑ok response", async () => {
    (global.fetch as any).mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => ({}),
    });
    await expect((api as any).fetchComments(token, 2)).rejects.toThrow("401");
  });

  test("fetchHistory performs GET and returns parsed JSON", async () => {
    const mockData = { events: [] };
    (global.fetch as any).mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => mockData,
    });
    const result = await (api as any).fetchHistory(token, 3);
    expect(global.fetch).toHaveBeenCalledWith("/api/tickets/3/history", {
      method: "GET",
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(result).toEqual(mockData);
  });

  test("fetchHistory throws on non‑ok response", async () => {
    (global.fetch as any).mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => ({}),
    });
    await expect((api as any).fetchHistory(token, 3)).rejects.toThrow("500");
  });

  test("addComment performs POST with body and returns parsed JSON", async () => {
    const body = "Nice work";
    const mockData = { id: 10, body };
    (global.fetch as any).mockResolvedValue({
      ok: true,
      status: 201,
      json: async () => mockData,
    });
    const result = await (api as any).addComment(token, 4, body);
    expect(global.fetch).toHaveBeenCalledWith("/api/tickets/4/comments", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ body }),
    });
    expect(result).toEqual(mockData);
  });

  test("addComment throws on non‑ok response", async () => {
    (global.fetch as any).mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({}),
    });
    await expect((api as any).addComment(token, 4, "bad")).rejects.toThrow("400");
  });
});
