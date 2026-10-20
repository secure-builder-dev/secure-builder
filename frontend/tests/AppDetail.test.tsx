// E3: frontend/src/App.tsx — opening a ticket in the Ticket details panel, its comments and its history.
import "@testing-library/jest-dom/vitest";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import App from "../src/App";
import { board, card, column, comment, event, mockApi, region, settle, signIn, ticket } from "./helpers";

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

const MINE = ticket({ id: 21, title: "Fix the sink", details: "It drips at night", priority: "urgent", status: "open",
  filed_by: "him", assigned_to: "her", group: 2 });
const OTHER = ticket({ id: 22, title: "Mow the lawn", status: "acknowledged", group: 2 });
const FILED = ticket({ id: 23, title: "Buy paint", filed_by: "her", assigned_to: "him", status: "open" });
const HOUSE = ticket({ id: 24, title: "Clean gutters", filed_by: "him", assigned_to: "her", status: "in_progress" });

function api(over = {}) {
  return mockApi({
    "GET /api/dashboard": { body: board({ todo: [MINE, OTHER] }) },
    "GET /api/filed": { body: { tickets: [FILED] } },
    "GET /api/board": { body: board({ todo: [MINE, OTHER, FILED], in_progress: [HOUSE] }) },
    ...over,
  });
}

async function open(title: string, inside: HTMLElement) {
  fireEvent.click(card(title, inside).querySelector(".card-title")!);
  await settle();
}

function panel() {
  return region("Ticket details");
}

describe("App: Ticket details", () => {
  it("shows no panel until a ticket is opened, and marks cards as openable", async () => {
    api();
    render(<App />);
    await signIn();
    expect(screen.queryByRole("region", { name: "Ticket details" })).toBeNull();
    expect(card("Fix the sink", column("My board", "To Do"))).toHaveClass("openable");
    expect(card("Buy paint", region("Tickets I filed"))).toHaveClass("openable");
    expect(card("Clean gutters", region("Household board"))).toHaveClass("openable");
  });

  it("opens a My board ticket: title, details and meta, after the directions and before New ticket", async () => {
    api();
    render(<App />);
    await signIn();
    await open("Fix the sink", column("My board", "To Do"));
    const p = panel();
    expect(p).toHaveClass("panel", "ticket-detail");
    expect(within(p).getByRole("heading", { level: 2 }).textContent).toBe("Fix the sink");
    expect(p.querySelector(".detail-text")!.textContent).toBe("It drips at night");
    expect(p.querySelector(".card-meta .badge.priority-urgent")).not.toBeNull();
    expect(p.querySelector(".card-meta .pill.status-open")).not.toBeNull();
    expect(screen.getByRole("main").contains(p)).toBe(true);
    expect(p.compareDocumentPosition(region("New ticket")) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("fetches that ticket's comments and history with the token and shows them oldest first", async () => {
    const calls = api({
      "GET /api/tickets/:id/comments": { body: { comments: [comment({ ticket_id: 21, author: "him", body: "Which tap?" }),
        comment({ ticket_id: 21, author: "her", body: "Kitchen" })] } },
      "GET /api/tickets/:id/history": { body: { events: [event({ ticket_id: 21, actor: "him", kind: "filed", to_status: "open" }),
        event({ ticket_id: 21, actor: "her", kind: "status", from_status: "acknowledged", to_status: "in_progress" }),
        event({ ticket_id: 21, actor: "him", kind: "edited", from_status: null, to_status: null })] } },
    });
    render(<App />);
    await signIn("tok-her");
    await open("Fix the sink", column("My board", "To Do"));
    const c = calls.calls("GET /api/tickets/:id/comments");
    const h = calls.calls("GET /api/tickets/:id/history");
    expect(c.map((x) => x.path)).toEqual(["/api/tickets/21/comments"]);
    expect(h.map((x) => x.path)).toEqual(["/api/tickets/21/history"]);
    expect(c[0].headers["authorization"]).toBe("Bearer tok-her");
    const list = within(panel()).getByRole("list", { name: "Comments" });
    const items = within(list).getAllByRole("listitem");
    expect(items.map((li) => li.querySelector(".comment-author")!.textContent)).toEqual(["him", "her"]);
    expect(items.map((li) => li.querySelector(".comment-body")!.textContent)).toEqual(["Which tap?", "Kitchen"]);
    const hist = within(panel()).getByRole("list", { name: "History" });
    expect(within(hist).getAllByRole("listitem").map((li) => li.textContent)).toEqual([
      "him filed it", "her moved it from acknowledged to in progress", "him edited it"]);
  });

  it("shows the empty texts when there are no comments or events", async () => {
    api();
    render(<App />);
    await signIn();
    await open("Fix the sink", column("My board", "To Do"));
    expect(within(panel()).getByText("No comments yet")).toHaveClass("empty");
    expect(within(panel()).getByText("No history")).toHaveClass("empty");
  });

  it("opens tickets from Tickets I filed and from the Household board, one at a time", async () => {
    const calls = api();
    render(<App />);
    await signIn();
    await open("Buy paint", region("Tickets I filed"));
    expect(within(panel()).getByRole("heading", { level: 2 }).textContent).toBe("Buy paint");
    await open("Clean gutters", region("Household board"));
    expect(screen.getAllByRole("region", { name: "Ticket details" })).toHaveLength(1);
    expect(within(panel()).getByRole("heading", { level: 2 }).textContent).toBe("Clean gutters");
    expect(calls.calls("GET /api/tickets/:id/comments").map((x) => x.path)).toEqual(
      ["/api/tickets/23/comments", "/api/tickets/24/comments"]);
  });

  it("opens a ticket with Enter on the focused title", async () => {
    api();
    render(<App />);
    await signIn();
    const target = card("Mow the lawn", column("My board", "To Do")).querySelector(".hover-target")!;
    fireEvent.keyDown(target, { key: "Enter" });
    await settle();
    expect(within(panel()).getByRole("heading", { level: 2 }).textContent).toBe("Mow the lawn");
  });

  it("Close details hides the panel, and Load closes it too", async () => {
    api();
    render(<App />);
    await signIn();
    await open("Fix the sink", column("My board", "To Do"));
    fireEvent.click(within(panel()).getByRole("button", { name: "Close details" }));
    expect(screen.queryByRole("region", { name: "Ticket details" })).toBeNull();
    await open("Fix the sink", column("My board", "To Do"));
    fireEvent.click(screen.getByRole("button", { name: "Load" }));
    await settle();
    expect(screen.queryByRole("region", { name: "Ticket details" })).toBeNull();
  });

  it("adds a comment: posts the stripped text, shows the answered comment last and empties the field", async () => {
    const calls = api({
      "GET /api/tickets/:id/comments": { body: { comments: [comment({ ticket_id: 21, author: "him", body: "First" })] } },
      "POST /api/tickets/:id/comments": { status: 201, body: comment({ ticket_id: 21, author: "her", body: "On it" }) },
    });
    render(<App />);
    await signIn("tok-her");
    await open("Fix the sink", column("My board", "To Do"));
    const box = within(panel()).getByLabelText("Comment") as HTMLTextAreaElement;
    fireEvent.change(box, { target: { value: "  On it  " } });
    fireEvent.click(within(panel()).getByRole("button", { name: "Add comment" }));
    await settle();
    const posts = calls.calls("POST /api/tickets/:id/comments");
    expect(posts).toHaveLength(1);
    expect(posts[0].path).toBe("/api/tickets/21/comments");
    expect(posts[0].body).toEqual({ body: "On it" });
    expect(posts[0].headers["authorization"]).toBe("Bearer tok-her");
    const items = within(within(panel()).getByRole("list", { name: "Comments" })).getAllByRole("listitem");
    expect(items.map((li) => li.querySelector(".comment-body")!.textContent)).toEqual(["First", "On it"]);
    expect(box.value).toBe("");
  });

  it("does not post a blank comment", async () => {
    const calls = api();
    render(<App />);
    await signIn();
    await open("Fix the sink", column("My board", "To Do"));
    fireEvent.change(within(panel()).getByLabelText("Comment"), { target: { value: "   " } });
    fireEvent.click(within(panel()).getByRole("button", { name: "Add comment" }));
    await settle();
    expect(calls.calls("POST /api/tickets/:id/comments")).toHaveLength(0);
  });

  it("a failed comment shows an alert in the panel and adds nothing", async () => {
    api({ "POST /api/tickets/:id/comments": { status: 400, body: { error: "invalid request" } } });
    render(<App />);
    await signIn();
    await open("Fix the sink", column("My board", "To Do"));
    fireEvent.change(within(panel()).getByLabelText("Comment"), { target: { value: "Hello" } });
    fireEvent.click(within(panel()).getByRole("button", { name: "Add comment" }));
    await settle();
    expect(within(panel()).getByRole("alert").textContent).toBe("Could not add the comment");
    expect(within(panel()).queryAllByRole("listitem").filter((li) => li.classList.contains("comment"))).toHaveLength(0);
  });

  it("failed or malformed comments and history answers leave those lists empty and the panel working", async () => {
    api({
      "GET /api/tickets/:id/comments": { status: 500, body: { error: "boom" } },
      "GET /api/tickets/:id/history": { raw: "not json" },
    });
    render(<App />);
    await signIn();
    await open("Fix the sink", column("My board", "To Do"));
    expect(within(panel()).getByRole("heading", { level: 2 }).textContent).toBe("Fix the sink");
    expect(within(panel()).getByText("No comments yet")).toBeInTheDocument();
    expect(within(panel()).getByText("No history")).toBeInTheDocument();
    expect(region("My board")).toBeInTheDocument();
  });

  it("shows comment text as text, never as markup", async () => {
    const marker = "<img src=x onerror=alert(1)>";
    api({ "GET /api/tickets/:id/comments": { body: { comments: [comment({ ticket_id: 21, body: marker })] } } });
    render(<App />);
    await signIn();
    await open("Fix the sink", column("My board", "To Do"));
    expect(panel().querySelector("img")).toBeNull();
    expect(within(panel()).getByText(marker)).toHaveClass("comment-body");
  });

  it("a status move made from a card fetches the open panel's history again", async () => {
    const calls = api();
    render(<App />);
    await signIn();
    await open("Fix the sink", column("My board", "To Do"));
    expect(calls.calls("GET /api/tickets/:id/history")).toHaveLength(1);
    fireEvent.click(within(card("Fix the sink", column("My board", "To Do"))).getByRole("button", { name: "Acknowledge" }));
    await settle();
    const h = calls.calls("GET /api/tickets/:id/history");
    expect(h).toHaveLength(2);
    expect(h[1].path).toBe("/api/tickets/21/history");
  });
});
