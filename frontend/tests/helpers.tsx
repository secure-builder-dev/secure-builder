// Shared test helpers (given by the plan; read-only). No app code is imported here, so every test file can use them
// before the component it tests exists.
import { expect, vi } from "vitest";
import { act, fireEvent, screen, waitFor, within } from "@testing-library/react";
import type { Board, CommentOut, Ticket, TicketEvent } from "../src/types";

let nextId = 100;

/** A ticket as the API answers it; any field can be overridden. */
export function ticket(over: Partial<Ticket> = {}): Ticket {
  const id = over.id ?? nextId++;
  return {
    id,
    title: `Ticket ${id}`,
    details: "",
    priority: "normal",
    due: null,
    status: "open",
    filed_by: "him",
    assigned_to: "her",
    created_at: "2026-10-01T09:00:00+00:00",
    updated_at: "2026-10-01T09:00:00+00:00",
    ...over,
  };
}

export function board(over: Partial<Board> = {}): Board {
  return { todo: [], in_progress: [], completed: [], ...over };
}

let nextNoteId = 500;

/** A comment as the API answers it. */
export function comment(over: Partial<CommentOut> = {}): CommentOut {
  return { id: nextNoteId++, ticket_id: 1, author: "her", body: "A comment", created_at: "2026-10-02T09:00:00+00:00", ...over };
}

/** A history event as the API answers it. */
export function event(over: Partial<TicketEvent> = {}): TicketEvent {
  return { id: nextNoteId++, ticket_id: 1, actor: "him", kind: "filed", from_status: null, to_status: "open",
    at: "2026-10-01T09:00:00+00:00", ...over };
}

export type Answer = { status?: number; body?: unknown; raw?: string };
export type Route = Answer | ((call: Call) => Answer);
export type Call = { method: string; path: string; query: Record<string, string>; headers: Record<string, string>; body: unknown };

/** Route keys: "GET /api/dashboard", "GET /api/filed", "GET /api/board", "GET /api/me", "GET /api/summary",
 *  "POST /api/tickets", "POST /api/tickets/:id/status", "GET /api/tickets/:id", "PATCH /api/tickets/:id",
 *  "GET /api/tickets/:id/comments", "POST /api/tickets/:id/comments", "GET /api/tickets/:id/history".
 *  The query string is not part of the key (it is in call.query). Unknown routes answer 404. */
export function mockApi(overrides: Record<string, Route> = {}) {
  const routes: Record<string, Route> = {
    "GET /api/dashboard": { body: board() },
    "GET /api/filed": { body: { tickets: [] } },
    "GET /api/board": { body: board() },
    "GET /api/me": { body: { user: "her" } },
    "POST /api/tickets": { status: 201, body: ticket({ filed_by: "her", assigned_to: "him" }) },
    "POST /api/tickets/:id/status": { body: ticket() },
    "GET /api/summary": { body: { overdue: 0, due_today: 0, open: 0 } },
    "GET /api/tickets/:id/comments": { body: { comments: [] } },
    "GET /api/tickets/:id/history": { body: { events: [] } },
    ...overrides,
  };
  const log: Call[] = [];
  const fn = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    const method = (init?.method ?? (input instanceof Request ? input.method : "GET")).toUpperCase();
    const parsed = new URL(url, "http://localhost");
    const path = parsed.pathname;
    const query: Record<string, string> = {};
    parsed.searchParams.forEach((v, k) => { query[k] = v; });
    const headers: Record<string, string> = {};
    new Headers(init?.headers ?? (input instanceof Request ? input.headers : undefined)).forEach((v, k) => {
      headers[k.toLowerCase()] = v;
    });
    let body: unknown = undefined;
    if (typeof init?.body === "string") {
      try { body = JSON.parse(init.body); } catch { body = init.body; }
    }
    const call: Call = { method, path, query, headers, body };
    log.push(call);
    const key = `${method} ${path.replace(/^\/api\/tickets\/\d+(?=\/|$)/, "/api/tickets/:id")}`;
    const route = routes[key];
    const answer: Answer = route === undefined ? { status: 404, body: { error: "not found" } }
      : typeof route === "function" ? route(call) : route;
    const text = answer.raw ?? JSON.stringify(answer.body ?? {});
    return new Response(text, { status: answer.status ?? 200, headers: { "Content-Type": "application/json" } });
  });
  globalThis.fetch = fn as unknown as typeof fetch;
  return {
    fn,
    routes,
    /** The calls made so far, optionally only those with this key's method and path (":id" matches any id). */
    calls(key?: string): Call[] {
      if (!key) return log;
      const [m, p] = key.split(" ");
      const re = new RegExp("^" + p.replace(":id", "\\d+") + "$");
      return log.filter((c) => c.method === m && re.test(c.path));
    },
  };
}

/** Type the token into the Token field, press Load, and let the answers settle. */
export async function signIn(token = "token-her") {
  fireEvent.change(screen.getByLabelText("Token"), { target: { value: token } });
  fireEvent.click(screen.getByRole("button", { name: "Load" }));
  await waitFor(() => expect(globalThis.fetch).toHaveBeenCalled());
  await settle();
}

/** Let pending fetch answers and state updates finish. */
export async function settle() {
  for (let i = 0; i < 5; i++) {
    await act(async () => { await new Promise((r) => setTimeout(r, 0)); });
  }
}

/** A labelled section (role region) of the page, e.g. region("My board"), region("Tickets I filed"). */
export function region(name: string, inside: HTMLElement = document.body) {
  return within(inside).getByRole("region", { name });
}

/** A column of a board section: column("My board", "To Do"). */
export function column(boardName: string, columnName: string) {
  return within(region(boardName)).getByRole("region", { name: columnName });
}

/** The TicketCard (an article named by its title) inside an element. */
export function card(title: string, inside: HTMLElement = document.body) {
  return within(inside).getByRole("article", { name: title });
}

export function cards(inside: HTMLElement = document.body) {
  return within(inside).queryAllByRole("article");
}
