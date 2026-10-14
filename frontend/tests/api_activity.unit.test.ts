import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import type { Ticket, Comments, History, CommentOut } from "../src/types";
import {
  fetchTicket,
  fetchComments,
  fetchHistory,
  addComment,
} from "../src/api";

describe("E3 API functions", () => {
  const originalFetch = global.fetch;
  let mockResponse: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    mockResponse = vi.fn();
    global.fetch = mockResponse as any;
  });

  afterEach(() => {
    global.fetch = originalFetch;
    vi.clearAllMocks();
  });

  describe("fetchTicket", () => {
    it("GETs /api/tickets/<id> with bearer token and returns parsed JSON", async () => {
      const ticket = { id: 1, title: "Test", details: "", priority: "normal" as const, due: null, status: "open" as const, filed_by: "her" as const, assigned_to: "him" as const, created_at: "2024-01-01T00:00:00Z", updated_at: "2024-01-01T00:00:00Z" };
      mockResponse.mockResolvedValueOnce({
        ok: true,
        json: async () => ticket,
      });

      const result = await fetchTicket("test-token", 1);

      expect(mockResponse).toHaveBeenCalledWith("/api/tickets/1", {
        method: "GET",
        headers: { Authorization: "Bearer test-token" },
      });
      expect(result).toEqual(ticket);
    });

    it("throws Error(String(status)) when response is not ok", async () => {
      mockResponse.mockResolvedValueOnce({
        ok: false,
        status: 404,
      });

      await expect(fetchTicket("test-token", 1)).rejects.toThrow("404");
    });
  });

  describe("fetchComments", () => {
    it("GETs /api/tickets/<id>/comments with bearer token and returns parsed JSON", async () => {
      const comments = { comments: [] };
      mockResponse.mockResolvedValueOnce({
        ok: true,
        json: async () => comments,
      });

      const result = await fetchComments("test-token", 1);

      expect(mockResponse).toHaveBeenCalledWith("/api/tickets/1/comments", {
        method: "GET",
        headers: { Authorization: "Bearer test-token" },
      });
      expect(result).toEqual(comments);
    });

    it("throws Error(String(status)) when response is not ok", async () => {
      mockResponse.mockResolvedValueOnce({
        ok: false,
        status: 401,
      });

      await expect(fetchComments("test-token", 1)).rejects.toThrow("401");
    });
  });

  describe("fetchHistory", () => {
    it("GETs /api/tickets/<id>/history with bearer token and returns parsed JSON", async () => {
      const history = { events: [] };
      mockResponse.mockResolvedValueOnce({
        ok: true,
        json: async () => history,
      });

      const result = await fetchHistory("test-token", 1);

      expect(mockResponse).toHaveBeenCalledWith("/api/tickets/1/history", {
        method: "GET",
        headers: { Authorization: "Bearer test-token" },
      });
      expect(result).toEqual(history);
    });

    it("throws Error(String(status)) when response is not ok", async () => {
      mockResponse.mockResolvedValueOnce({
        ok: false,
        status: 500,
      });

      await expect(fetchHistory("test-token", 1)).rejects.toThrow("500");
    });
  });

  describe("addComment", () => {
    it("POSTs {body: body} as JSON to /api/tickets/<id>/comments with bearer token and returns parsed comment", async () => {
      const comment = { id: 1, ticket_id: 1, author: "her" as const, body: "Test comment", created_at: "2024-01-01T00:00:00Z" };
      mockResponse.mockResolvedValueOnce({
        ok: true,
        json: async () => comment,
      });

      const result = await addComment("test-token", 1, "Test comment");

      expect(mockResponse).toHaveBeenCalledWith("/api/tickets/1/comments", {
        method: "POST",
        headers: {
          Authorization: "Bearer test-token",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ body: "Test comment" }),
      });
      expect(result).toEqual(comment);
    });

    it("throws Error(String(status)) when response is not ok", async () => {
      mockResponse.mockResolvedValueOnce({
        ok: false,
        status: 400,
      });

      await expect(addComment("test-token", 1, "Test comment")).rejects.toThrow("400");
    });
  });
});
