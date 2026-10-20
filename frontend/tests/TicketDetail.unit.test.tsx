// TO-3h: frontend/src/TicketDetail.tsx — the Ticket details panel.
import "@testing-library/jest-dom/vitest";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import TicketDetail from "../src/TicketDetail";
import { comment, event, mockApi, region, settle, ticket } from "./helpers";

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

// Filed by him, so the panel shows no Edit button for "her" (E4) and the E3 checks stay exact.
const T = ticket({ id: 41, title: "Fix the sink", details: "Left pipe drips", priority: "urgent", due: "2026-11-01",
  status: "in_progress", filed_by: "him", assigned_to: "her" });

function panel() {
  return region("Ticket details");
}

function show(t = T, onClose = () => {}) {
  return render(<TicketDetail token="tok-d" ticket={t} me="her" onClose={onClose} />);
}

function field() {
  return within(panel()).getByRole("textbox", { name: "Comment" });
}

describe("TicketDetail: markup", () => {
  it("is a section.panel.ticket-detail named Ticket details with an h2 holding the title", async () => {
    mockApi();
    show();
    const p = panel();
    expect(p.tagName).toBe("SECTION");
    expect(p).toHaveClass("panel", "ticket-detail");
    const h2 = within(p).getByRole("heading", { level: 2, name: "Fix the sink" });
    expect(h2.textContent).toBe("Fix the sink");
    await settle();
  });

  it("shows the details in p.detail-text", async () => {
    mockApi();
    show();
    const d = within(panel()).getByText("Left pipe drips");
    expect(d.tagName).toBe("P");
    expect(d).toHaveClass("detail-text");
    await settle();
  });

  it("has no p.detail-text when the details are empty", async () => {
    mockApi();
    show(ticket({ id: 42, title: "Bare", details: "" }));
    expect(panel().querySelector(".detail-text")).toBeNull();
    await settle();
  });

  it("has a div.card-meta with the same badge, due, pill and who spans as TicketCard", async () => {
    mockApi();
    show();
    const meta = panel().querySelector("div.card-meta") as HTMLElement;
    expect(meta).not.toBeNull();
    const badge = within(meta).getByText("urgent");
    expect(badge.tagName).toBe("SPAN");
    expect(badge).toHaveClass("badge", "priority-urgent");
    const due = within(meta).getByText("due 2026-11-01");
    expect(due.tagName).toBe("SPAN");
    expect(due).toHaveClass("due");
    const pill = within(meta).getByText("in progress");
    expect(pill.tagName).toBe("SPAN");
    expect(pill).toHaveClass("pill", "status-in_progress");
    const who = within(meta).getByText("for her");
    expect(who.tagName).toBe("SPAN");
    expect(who).toHaveClass("who");
    await settle();
  });

  it("has no due span without a due date", async () => {
    mockApi();
    show(ticket({ id: 43, title: "Undated", due: null, priority: "low", status: "open", assigned_to: "him" }));
    const meta = panel().querySelector("div.card-meta") as HTMLElement;
    expect(meta.querySelector(".due")).toBeNull();
    expect(within(meta).getByText("low")).toHaveClass("badge", "priority-low");
    expect(within(meta).getByText("open")).toHaveClass("pill", "status-open");
    expect(within(meta).getByText("for him")).toHaveClass("who");
    await settle();
  });

  it("has a Comments h3 followed by the CommentThread and a History h3 followed by the HistoryList", async () => {
    mockApi({
      "GET /api/tickets/:id/comments": { body: { comments: [comment({ ticket_id: 41, body: "Soon please" })] } },
      "GET /api/tickets/:id/history": { body: { events: [event({ ticket_id: 41, actor: "him", kind: "filed" })] } },
    });
    show();
    const p = panel();
    await within(p).findByText("Soon please");
    await within(p).findByText("him filed it");
    const hc = within(p).getByRole("heading", { level: 3, name: "Comments" });
    const hh = within(p).getByRole("heading", { level: 3, name: "History" });
    const thread = p.querySelector(".comment-thread") as HTMLElement;
    const history = within(p).getByRole("list", { name: "History" });
    expect(thread).not.toBeNull();
    expect(hc.compareDocumentPosition(thread) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(thread.compareDocumentPosition(hh) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(hh.compareDocumentPosition(history) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("has a Close details button with the class close-detail that calls onClose", async () => {
    mockApi();
    const onClose = vi.fn();
    show(T, onClose);
    const btn = within(panel()).getByRole("button", { name: "Close details" });
    expect(btn).toHaveClass("close-detail");
    expect(onClose).not.toHaveBeenCalled();
    fireEvent.click(btn);
    expect(onClose).toHaveBeenCalledTimes(1);
    await settle();
  });
});

describe("TicketDetail: loading comments and history", () => {
  it("fetches the ticket's comments and history with the token when it opens and shows them", async () => {
    const api = mockApi({
      "GET /api/tickets/:id/comments": { body: { comments: [
        comment({ ticket_id: 41, author: "her", body: "First" }),
        comment({ ticket_id: 41, author: "him", body: "Second" }),
      ] } },
      "GET /api/tickets/:id/history": { body: { events: [
        event({ ticket_id: 41, actor: "him", kind: "filed", to_status: "open" }),
        event({ ticket_id: 41, actor: "her", kind: "status", from_status: "open", to_status: "acknowledged" }),
      ] } },
    });
    show();
    const p = panel();
    await waitFor(() => expect(within(p).getAllByRole("listitem").length).toBe(4));
    const comments = within(within(p).getByRole("list", { name: "Comments" })).getAllByRole("listitem");
    expect(comments.map((li) => li.querySelector(".comment-body")!.textContent)).toEqual(["First", "Second"]);
    const history = within(within(p).getByRole("list", { name: "History" })).getAllByRole("listitem");
    expect(history.map((li) => li.textContent)).toEqual(["him filed it", "her moved it from open to acknowledged"]);
    const cc = api.calls("GET /api/tickets/:id/comments");
    const hc = api.calls("GET /api/tickets/:id/history");
    expect(cc.length).toBeGreaterThanOrEqual(1);
    expect(hc.length).toBeGreaterThanOrEqual(1);
    for (const c of [...cc, ...hc]) {
      expect(c.path.startsWith("/api/tickets/41/")).toBe(true);
      expect(c.headers["authorization"]).toBe("Bearer tok-d");
    }
  });

  it("fetches again when ticket.id changes", async () => {
    const api = mockApi({
      "GET /api/tickets/:id/comments": (call) => ({ body: { comments: [
        comment({ ticket_id: Number(call.path.split("/")[3]), body: `note on ${call.path.split("/")[3]}` }),
      ] } }),
    });
    const { rerender } = show();
    await within(panel()).findByText("note on 41");
    const other = ticket({ id: 77, title: "Mow the lawn", filed_by: "him", assigned_to: "her" });
    rerender(<TicketDetail token="tok-d" ticket={other} me="her" onClose={() => {}} />);
    await within(panel()).findByText("note on 77");
    expect(within(panel()).getByRole("heading", { level: 2, name: "Mow the lawn" })).toBeInTheDocument();
    expect(api.calls("GET /api/tickets/:id/comments").some((c) => c.path === "/api/tickets/77/comments")).toBe(true);
    expect(api.calls("GET /api/tickets/:id/history").some((c) => c.path === "/api/tickets/77/history")).toBe(true);
    expect(within(panel()).queryByText("note on 41")).toBeNull();
  });

  it("a failed comments answer leaves the comments empty while the rest of the panel works", async () => {
    mockApi({
      "GET /api/tickets/:id/comments": { status: 500, body: { error: "x" } },
      "GET /api/tickets/:id/history": { body: { events: [event({ ticket_id: 41, actor: "him", kind: "filed" })] } },
    });
    const onClose = vi.fn();
    show(T, onClose);
    const p = panel();
    await within(p).findByText("him filed it");
    await settle();
    expect(p.querySelectorAll("li.comment")).toHaveLength(0);
    expect(within(p).getByText("No comments yet")).toBeInTheDocument();
    expect(within(p).getByRole("heading", { level: 2, name: "Fix the sink" })).toBeInTheDocument();
    fireEvent.click(within(p).getByRole("button", { name: "Close details" }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("a malformed history answer leaves the history empty while the rest of the panel works", async () => {
    mockApi({
      "GET /api/tickets/:id/comments": { body: { comments: [comment({ ticket_id: 41, body: "Still here" })] } },
      "GET /api/tickets/:id/history": { raw: "<html>oops</html>" },
    });
    show();
    const p = panel();
    await within(p).findByText("Still here");
    await settle();
    expect(within(p).queryByRole("list", { name: "History" })).toBeNull();
    expect(within(p).getByText("No history")).toBeInTheDocument();
  });

  it("answers of the wrong shape leave both lists empty", async () => {
    mockApi({
      "GET /api/tickets/:id/comments": { body: { nothing: true } },
      "GET /api/tickets/:id/history": { body: { events: "nope" } },
    });
    show();
    await settle();
    const p = panel();
    expect(within(p).getByText("No comments yet")).toBeInTheDocument();
    expect(within(p).getByText("No history")).toBeInTheDocument();
    expect(within(p).getByRole("heading", { level: 2, name: "Fix the sink" })).toBeInTheDocument();
    expect(within(p).getByRole("button", { name: "Close details" })).toBeInTheDocument();
  });
});

describe("TicketDetail: adding a comment", () => {
  it("POSTs the comment and shows the answered comment at the end of the list", async () => {
    const api = mockApi({
      "GET /api/tickets/:id/comments": { body: { comments: [comment({ ticket_id: 41, author: "him", body: "Earlier" })] } },
      "POST /api/tickets/:id/comments": { status: 201, body: comment({ ticket_id: 41, author: "her", body: "From the server" }) },
    });
    show();
    const p = panel();
    await within(p).findByText("Earlier");
    fireEvent.change(field(), { target: { value: "  Typed text  " } });
    fireEvent.click(within(p).getByRole("button", { name: "Add comment" }));
    await within(p).findByText("From the server");
    const posts = api.calls("POST /api/tickets/:id/comments");
    expect(posts).toHaveLength(1);
    expect(posts[0].path).toBe("/api/tickets/41/comments");
    expect(posts[0].headers["authorization"]).toBe("Bearer tok-d");
    expect(posts[0].body).toEqual({ body: "Typed text" });
    const items = within(within(p).getByRole("list", { name: "Comments" })).getAllByRole("listitem");
    expect(items.map((li) => li.querySelector(".comment-body")!.textContent)).toEqual(["Earlier", "From the server"]);
    expect(items[1].querySelector(".comment-author")!.textContent).toBe("her");
    expect(within(p).queryByRole("alert")).toBeNull();
  });

  it("adds the first comment to an empty thread", async () => {
    mockApi({
      "POST /api/tickets/:id/comments": { status: 201, body: comment({ ticket_id: 41, author: "her", body: "First!" }) },
    });
    show();
    await settle();
    fireEvent.change(field(), { target: { value: "First!" } });
    fireEvent.click(within(panel()).getByRole("button", { name: "Add comment" }));
    await within(panel()).findByText("First!");
    expect(within(panel()).queryByText("No comments yet")).toBeNull();
  });

  it("a failed POST shows p.error with role alert inside the panel and adds nothing", async () => {
    mockApi({
      "GET /api/tickets/:id/comments": { body: { comments: [comment({ ticket_id: 41, body: "Earlier" })] } },
      "POST /api/tickets/:id/comments": { status: 500, body: { error: "x" } },
    });
    show();
    const p = panel();
    await within(p).findByText("Earlier");
    fireEvent.change(field(), { target: { value: "Will fail" } });
    fireEvent.click(within(p).getByRole("button", { name: "Add comment" }));
    const alert = await within(p).findByRole("alert");
    expect(alert.tagName).toBe("P");
    expect(alert).toHaveClass("error");
    expect(alert.textContent).toBe("Could not add the comment");
    expect(p.querySelectorAll("li.comment")).toHaveLength(1);
    expect(screen.getAllByRole("alert")).toHaveLength(1);
  });
});
