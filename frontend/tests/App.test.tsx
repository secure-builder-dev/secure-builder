// GD-1i: frontend/src/App.tsx — top bar, token, Load, the personal board and the error messages.
import "@testing-library/jest-dom/vitest";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import App from "../src/App";
import { board, card, cards, column, mockApi, region, settle, signIn, ticket } from "./helpers";

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

const DASH = board({
  todo: [ticket({ title: "Fix sink", group: 0, priority: "urgent" }), ticket({ title: "Buy milk", group: 2, due: "2026-11-01" })],
  in_progress: [ticket({ title: "Paint fence", status: "in_progress", group: 1 })],
  completed: [ticket({ title: "Mow lawn", status: "done" })],
});

describe("App", () => {
  it("has a top bar (header.topbar) with the brand heading ~/honey-do, the Token field and the Load button", () => {
    mockApi();
    render(<App />);
    const bar = screen.getByRole("banner");
    expect(bar).toHaveClass("topbar");
    expect(within(bar).getByRole("heading", { level: 1, name: "~/honey-do" })).toHaveClass("brand");
    expect(within(bar).getByLabelText("Token")).toBeInTheDocument();
    expect(within(bar).getByRole("button", { name: "Load" })).toBeInTheDocument();
    expect(document.querySelector(".app")).not.toBeNull();
  });

  it("the Token field is a password input", () => {
    mockApi();
    render(<App />);
    expect(screen.getByLabelText("Token")).toHaveAttribute("type", "password");
  });

  it("fetches nothing until a token is entered and Load is pressed", async () => {
    const api = mockApi();
    render(<App />);
    fireEvent.change(screen.getByLabelText("Token"), { target: { value: "tok" } });
    await settle();
    expect(api.fn).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Load" }));
    await settle();
    expect(api.calls("GET /api/dashboard")).toHaveLength(1);
    expect(api.calls("GET /api/dashboard")[0].headers["authorization"]).toBe("Bearer tok");
  });

  it("never writes the token to localStorage or sessionStorage", async () => {
    mockApi();
    const local = vi.spyOn(Storage.prototype, "setItem");
    render(<App />);
    await signIn("secret-token");
    expect(local).not.toHaveBeenCalled();
    expect(JSON.stringify({ ...localStorage, ...sessionStorage })).not.toContain("secret-token");
  });

  it("shows My board with the columns To Do, In Progress and Completed inside one .board", async () => {
    mockApi({ "GET /api/dashboard": { body: DASH } });
    render(<App />);
    await signIn();
    const mine = region("My board");
    expect(mine).toHaveClass("panel");
    expect(within(mine).getByRole("heading", { level: 2, name: "My board" })).toBeInTheDocument();
    const grid = mine.querySelector(".board")!;
    expect(grid).not.toBeNull();
    for (const name of ["To Do", "In Progress", "Completed"]) {
      const col = column("My board", name);
      expect(col).toHaveClass("column");
      expect(grid.contains(col)).toBe(true);
    }
  });

  it("puts each ticket of /api/dashboard on its own card in its column", async () => {
    mockApi({ "GET /api/dashboard": { body: DASH } });
    render(<App />);
    await signIn();
    expect(cards(column("My board", "To Do")).map((c) => c.getAttribute("aria-label"))).toEqual(["Fix sink", "Buy milk"]);
    expect(cards(column("My board", "In Progress")).map((c) => c.getAttribute("aria-label"))).toEqual(["Paint fence"]);
    expect(cards(column("My board", "Completed")).map((c) => c.getAttribute("aria-label"))).toEqual(["Mow lawn"]);
    for (const c of cards(region("My board"))) expect(c).toHaveClass("card");
  });

  it("shows each ticket's title, priority and due date on its card", async () => {
    mockApi({ "GET /api/dashboard": { body: DASH } });
    render(<App />);
    await signIn();
    const milk = card("Buy milk", region("My board"));
    expect(within(milk).getByRole("heading", { name: "Buy milk" })).toBeInTheDocument();
    expect(within(milk).getByText("normal")).toBeInTheDocument();
    expect(within(milk).getByText("due 2026-11-01")).toBeInTheDocument();
  });

  it("marks a group-0 ticket urgent", async () => {
    mockApi({ "GET /api/dashboard": { body: DASH } });
    render(<App />);
    await signIn();
    expect(card("Fix sink", region("My board"))).toHaveClass("card", "urgent");
    expect(card("Buy milk", region("My board"))).not.toHaveClass("urgent");
  });

  it("shows each column's ticket count in its .column-title heading", async () => {
    mockApi({ "GET /api/dashboard": { body: DASH } });
    render(<App />);
    await signIn();
    const title = column("My board", "To Do").querySelector(".column-title")!;
    expect(title.tagName).toBe("H3");
    expect(title.textContent).toContain("To Do");
    expect(title.querySelector(".count")!.textContent).toBe("2");
    expect(column("My board", "Completed").querySelector(".count")!.textContent).toBe("1");
  });

  it("shows 'Nothing here' in an empty column", async () => {
    mockApi({ "GET /api/dashboard": { body: board({ todo: [ticket({ title: "Only" })] }) } });
    render(<App />);
    await signIn();
    expect(within(column("My board", "In Progress")).getByText("Nothing here")).toHaveClass("empty");
    expect(within(column("My board", "To Do")).queryByText("Nothing here")).toBeNull();
    expect(column("My board", "In Progress").querySelector(".count")!.textContent).toBe("0");
  });

  it("shows Wrong token when the dashboard answers 401, and no board", async () => {
    mockApi({ "GET /api/dashboard": { status: 401, body: { error: "unauthorized" } },
              "GET /api/filed": { status: 401, body: { error: "unauthorized" } } });
    render(<App />);
    await signIn("bad");
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Wrong token");
    expect(alert).toHaveClass("error");
    expect(screen.queryByRole("region", { name: "My board" })).toBeNull();
  });

  it("shows Something went wrong on any other error, never the response body", async () => {
    mockApi({ "GET /api/dashboard": { status: 500, body: { error: "secret stack trace" } } });
    render(<App />);
    await signIn();
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Something went wrong");
    expect(document.body.textContent).not.toContain("secret stack trace");
  });

  it("shows no error message after a successful Load", async () => {
    mockApi({ "GET /api/dashboard": { body: DASH } });
    render(<App />);
    await signIn();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("clears an earlier error after a successful Load", async () => {
    const api = mockApi({ "GET /api/dashboard": { status: 401, body: {} } });
    render(<App />);
    await signIn("bad");
    expect(await screen.findByRole("alert")).toHaveTextContent("Wrong token");
    api.routes["GET /api/dashboard"] = { body: DASH };
    await signIn("good");
    expect(screen.queryByRole("alert")).toBeNull();
    expect(card("Fix sink", region("My board"))).toBeInTheDocument();
  });

  it("renders ticket text as text, never as HTML", async () => {
    mockApi({ "GET /api/dashboard": { body: board({ todo: [ticket({ title: "<b>bold</b>" })] }) } });
    render(<App />);
    await signIn();
    expect(screen.getAllByText("<b>bold</b>").length).toBeGreaterThan(0);
    expect(document.querySelector("main b")).toBeNull();
  });
});
