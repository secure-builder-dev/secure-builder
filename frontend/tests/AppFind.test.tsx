// E4: frontend/src/App.tsx — the household board's filter bar and the summary badge in the top bar.
import "@testing-library/jest-dom/vitest";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import App from "../src/App";
import { board, card, column, mockApi, region, settle, signIn, ticket } from "./helpers";

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

const OPEN = ticket({ id: 41, title: "Open one", status: "open", group: 2 });

function bar() {
  return within(region("Household board")).getByRole("search", { name: "Filter household board" });
}

function apply(q: string, priority: string, assignedTo: string) {
  const f = bar();
  fireEvent.change(within(f).getByLabelText("Search"), { target: { value: q } });
  fireEvent.change(within(f).getByLabelText("Priority"), { target: { value: priority } });
  fireEvent.change(within(f).getByLabelText("Assigned to"), { target: { value: assignedTo } });
  fireEvent.click(within(f).getByRole("button", { name: "Apply" }));
}

describe("App: filter bar", () => {
  it("puts the filter bar inside the Household board with Search, Priority, Assigned to and Apply", async () => {
    mockApi();
    render(<App />);
    await signIn();
    const f = bar();
    expect(f.tagName).toBe("FORM");
    expect(f).toHaveClass("filter-bar");
    const prio = within(f).getByLabelText("Priority") as HTMLSelectElement;
    expect([...prio.options].map((o) => [o.value, o.textContent])).toEqual(
      [["", "Any"], ["low", "low"], ["normal", "normal"], ["urgent", "urgent"]]);
    const who = within(f).getByLabelText("Assigned to") as HTMLSelectElement;
    expect([...who.options].map((o) => [o.value, o.textContent])).toEqual([["", "Anyone"], ["her", "her"], ["him", "him"]]);
    expect(within(f).getByLabelText("Search")).toBeInTheDocument();
  });

  it("Apply fetches /api/board again with only the non-empty filter fields, and shows the answer", async () => {
    const calls = mockApi({
      "GET /api/board": (c) => ({ body: c.query.q === "sink" ? board({ todo: [ticket({ title: "Sink" })] }) : board() }),
    });
    render(<App />);
    await signIn("tok-her");
    expect(calls.calls("GET /api/board")[0].query).toEqual({});
    apply("  sink ", "urgent", "");
    await settle();
    const boards = calls.calls("GET /api/board");
    expect(boards).toHaveLength(2);
    expect(boards[1].query).toEqual({ q: "sink", priority: "urgent" });
    expect(boards[1].headers["authorization"]).toBe("Bearer tok-her");
    expect(card("Sink", column("Household board", "To Do"))).toBeInTheDocument();
  });

  it("keeps the filter for later board fetches", async () => {
    const calls = mockApi({ "GET /api/dashboard": { body: board({ todo: [OPEN] }) } });
    render(<App />);
    await signIn();
    apply("", "", "him");
    await settle();
    fireEvent.click(within(card("Open one", column("My board", "To Do"))).getByRole("button", { name: "Acknowledge" }));
    await settle();
    const boards = calls.calls("GET /api/board");
    expect(boards.length).toBeGreaterThanOrEqual(3);
    expect(boards[boards.length - 1].query).toEqual({ assigned_to: "him" });
  });
});

describe("App: summary badge", () => {
  it("shows the caller's summary in the top bar after Load", async () => {
    const calls = mockApi({ "GET /api/summary": { body: { overdue: 0, due_today: 1, open: 5 } } });
    render(<App />);
    expect(screen.queryByLabelText("Summary")).toBeNull();
    await signIn("tok-him");
    const s = within(screen.getByRole("banner")).getByLabelText("Summary");
    expect(s).toHaveClass("summary");
    expect(s).not.toHaveClass("alert");
    expect(s.textContent).toBe("0 overdue · 1 due today · 5 open");
    expect(calls.calls("GET /api/summary")[0].headers["authorization"]).toBe("Bearer tok-him");
  });

  it("marks the badge alert when something is overdue", async () => {
    mockApi({ "GET /api/summary": { body: { overdue: 2, due_today: 0, open: 3 } } });
    render(<App />);
    await signIn();
    expect(screen.getByLabelText("Summary")).toHaveClass("summary", "alert");
  });

  it("fetches the summary again after a status move and after a new ticket", async () => {
    const calls = mockApi({ "GET /api/dashboard": { body: board({ todo: [OPEN] }) } });
    render(<App />);
    await signIn();
    expect(calls.calls("GET /api/summary")).toHaveLength(1);
    fireEvent.click(within(card("Open one", column("My board", "To Do"))).getByRole("button", { name: "Acknowledge" }));
    await settle();
    expect(calls.calls("GET /api/summary")).toHaveLength(2);
    fireEvent.change(within(region("New ticket")).getByLabelText("Title"), { target: { value: "Another" } });
    fireEvent.click(within(region("New ticket")).getByRole("button", { name: "File ticket" }));
    await settle();
    expect(calls.calls("GET /api/summary")).toHaveLength(3);
  });

  it("a failed or malformed summary shows no badge and leaves the page working", async () => {
    mockApi({ "GET /api/summary": { status: 500, body: { error: "boom" } } });
    render(<App />);
    await signIn();
    expect(screen.queryByLabelText("Summary")).toBeNull();
    expect(region("My board")).toBeInTheDocument();
    cleanup();
    mockApi({ "GET /api/summary": { body: { overdue: "lots" } } });
    render(<App />);
    await signIn();
    expect(screen.queryByLabelText("Summary")).toBeNull();
  });
});
