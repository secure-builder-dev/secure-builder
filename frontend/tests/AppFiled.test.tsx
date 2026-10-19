// GD-1k: frontend/src/App.tsx — Tickets I filed: every filed ticket on its own card, Close and Reopen on done ones.
import "@testing-library/jest-dom/vitest";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import App from "../src/App";
import { card, cards, mockApi, region, settle, signIn, ticket } from "./helpers";

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

const MINE = [
  ticket({ id: 21, title: "Clean garage", status: "open", filed_by: "her", assigned_to: "him" }),
  ticket({ id: 22, title: "Fix shelf", status: "done", filed_by: "her", assigned_to: "him", due: "2026-10-12" }),
  ticket({ id: 23, title: "Wash car", status: "closed", filed_by: "her", assigned_to: "him" }),
];

function filedPanel() {
  return region("Tickets I filed");
}

describe("App: Tickets I filed", () => {
  it("shows a Tickets I filed panel with a heading and a .card-list", async () => {
    mockApi({ "GET /api/filed": { body: { tickets: MINE } } });
    render(<App />);
    await signIn();
    const p = filedPanel();
    expect(p).toHaveClass("panel");
    expect(within(p).getByRole("heading", { level: 2, name: "Tickets I filed" })).toBeInTheDocument();
    expect(p.querySelector(".card-list")).not.toBeNull();
  });

  it("puts every filed ticket on its own card, in the order of /api/filed, inside the .card-list", async () => {
    mockApi({ "GET /api/filed": { body: { tickets: MINE } } });
    render(<App />);
    await signIn();
    const list = filedPanel().querySelector(".card-list") as HTMLElement;
    const got = cards(list);
    expect(got.map((c) => c.getAttribute("aria-label"))).toEqual(["Clean garage", "Fix shelf", "Wash car"]);
    for (const c of got) expect(c).toHaveClass("card");
  });

  it("each filed card shows its status, priority, due date and who it is for", async () => {
    mockApi({ "GET /api/filed": { body: { tickets: MINE } } });
    render(<App />);
    await signIn();
    const shelf = card("Fix shelf", filedPanel());
    expect(within(shelf).getByText("done")).toHaveClass("pill");
    expect(within(shelf).getByText("normal")).toHaveClass("badge");
    expect(within(shelf).getByText("due 2026-10-12")).toBeInTheDocument();
    expect(within(shelf).getByText("for him")).toBeInTheDocument();
  });

  it("only a done ticket has Close and Reopen", async () => {
    mockApi({ "GET /api/filed": { body: { tickets: MINE } } });
    render(<App />);
    await signIn();
    expect(within(card("Fix shelf", filedPanel())).getAllByRole("button").map((b) => b.textContent)).toEqual(["Close", "Reopen"]);
    expect(within(card("Clean garage", filedPanel())).queryAllByRole("button")).toHaveLength(0);
    expect(within(card("Wash car", filedPanel())).queryAllByRole("button")).toHaveLength(0);
  });

  it.each([["Close", "closed"], ["Reopen", "open"]])("%s posts its move for the ticket and reloads", async (button, status) => {
    const api = mockApi({ "GET /api/filed": { body: { tickets: MINE } } });
    render(<App />);
    await signIn("tok-her");
    fireEvent.click(within(card("Fix shelf", filedPanel())).getByRole("button", { name: button }));
    await settle();
    const [post] = api.calls("POST /api/tickets/:id/status");
    expect(post.path).toBe("/api/tickets/22/status");
    expect(post.body).toEqual({ status });
    expect(api.calls("GET /api/filed")).toHaveLength(2);
    expect(api.calls("GET /api/dashboard")).toHaveLength(2);
  });

  it("a newly filed ticket lands on a card of its own in Tickets I filed", async () => {
    const fresh = ticket({ id: 30, title: "Brand new", filed_by: "her", assigned_to: "him", priority: "urgent" });
    const api = mockApi({ "GET /api/filed": { body: { tickets: MINE } }, "POST /api/tickets": { status: 201, body: fresh } });
    render(<App />);
    await signIn();
    expect(cards(filedPanel())).toHaveLength(3);
    api.routes["GET /api/filed"] = { body: { tickets: [fresh, ...MINE] } };
    const f = region("New ticket");
    fireEvent.change(within(f).getByLabelText("Title"), { target: { value: "Brand new" } });
    fireEvent.click(within(f).getByRole("button", { name: "File ticket" }));
    await settle();
    const got = cards(filedPanel());
    expect(got).toHaveLength(4);
    const mine = card("Brand new", filedPanel());
    expect(got[0]).toBe(mine);
    expect(mine).toHaveClass("card");
    expect(within(mine).getByText("urgent")).toHaveClass("badge");
    expect(within(mine).queryByText("Clean garage")).toBeNull();
  });

  it("shows no Tickets I filed panel before Load", () => {
    mockApi();
    render(<App />);
    expect(screen.queryByRole("region", { name: "Tickets I filed" })).toBeNull();
  });
});
