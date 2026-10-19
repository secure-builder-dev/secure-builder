// Unit tests for the new API functions added in E4.
import { expect, test, vi } from "vitest";
import { editTicket, fetchSummary, fetchBoard } from "../src/api";

/** Helper to stub global fetch and return a controllable mock response. */
function mockFetch(response: Partial<Response> & { json?: () => any }) {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    json: () => Promise.resolve({}),
    ...response,
  } as Response);
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

test("editTicket sends PATCH with token and body and returns parsed ticket", async () => {
  const ticket = { id: 1, title: "New" };
  const fetchMock = mockFetch({ ok: true, json: () => Promise.resolve(ticket) });

  const result = await editTicket("my-token", 42, { title: "New" });

  expect(fetchMock).toHaveBeenCalledOnce();
  const [url, init] = fetchMock.mock.calls[0];
  expect(url).toBe("/api/tickets/42");
  expect(init?.method).toBe("PATCH");
  expect(init?.headers).toEqual({
    Authorization: "Bearer my-token",
    "Content-Type": "application/json",
  });
  expect(init?.body).toBe(JSON.stringify({ title: "New" }));
  expect(result).toEqual(ticket);
});

test("editTicket throws Error with status on non-ok response", async () => {
  const fetchMock = mockFetch({ ok: false, status: 403 });
  await expect(editTicket("t", 1, { title: "x" })).rejects.toThrowError("403");
  expect(fetchMock).toHaveBeenCalledOnce();
});

test("fetchSummary GETs /api/summary with token and returns parsed summary", async () => {
  const summary = { overdue: 2, due_today: 1, open: 5 };
  const fetchMock = mockFetch({ ok: true, json: () => Promise.resolve(summary) });

  const result = await fetchSummary("tok");

  expect(fetchMock).toHaveBeenCalledOnce();
  const [url, init] = fetchMock.mock.calls[0];
  expect(url).toBe("/api/summary");
  expect(init?.method).toBe("GET");
  expect(init?.headers).toEqual({ Authorization: "Bearer tok" });
  expect(result).toEqual(summary);
});

test("fetchSummary throws Error with status on non-ok response", async () => {
  const fetchMock = mockFetch({ ok: false, status: 500 });
  await expect(fetchSummary("tok")).rejects.toThrowError("500");
});

test("fetchBoard without filter calls plain /api/board", async () => {
  const board = { todo: [], in_progress: [], completed: [] };
  const fetchMock = mockFetch({ ok: true, json: () => Promise.resolve(board) });

  const result = await fetchBoard("tok");

  expect(fetchMock).toHaveBeenCalledOnce();
  const [url, init] = fetchMock.mock.calls[0];
  expect(url).toBe("/api/board");
  expect(init?.method).toBe("GET");
  expect(init?.headers).toEqual({ Authorization: "Bearer tok" });
  expect(result).toEqual(board);
});

test("fetchBoard with filter includes only non‑empty fields as query parameters", async () => {
  const board = { todo: [], in_progress: [], completed: [] };
  const fetchMock = mockFetch({ ok: true, json: () => Promise.resolve(board) });

  const result = await fetchBoard("tok", { q: "test", priority: "", assigned_to: "" });

  expect(fetchMock).toHaveBeenCalledOnce();
  const [url] = fetchMock.mock.calls[0];
  expect(url).toBe("/api/board?q=test");
  expect(result).toEqual(board);
});

test("fetchBoard with multiple non‑empty filter fields builds correct query string", async () => {
  const board = { todo: [], in_progress: [], completed: [] };
  const fetchMock = mockFetch({ ok: true, json: () => Promise.resolve(board) });

  const result = await fetchBoard("tok", {
    q: "foo",
    priority: "urgent",
    assigned_to: "her",
  });

  expect(fetchMock).toHaveBeenCalledOnce();
  const [url] = fetchMock.mock.calls[0];
  const params = new URLSearchParams(url.split("?")[1]);
  expect(url.startsWith("/api/board?")).toBe(true);
  expect(params.get("q")).toBe("foo");
  expect(params.get("priority")).toBe("urgent");
  expect(params.get("assigned_to")).toBe("her");
  expect(result).toEqual(board);
});

test("fetchBoard throws Error with status on non-ok response", async () => {
  const fetchMock = mockFetch({ ok: false, status: 404 });
  await expect(fetchBoard("tok")).rejects.toThrowError("404");
});
