// GD-1j: frontend/src/App.tsx — the New ticket form and the Acknowledge / Start / Done buttons.
import "@testing-library/jest-dom/vitest";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import App from "../src/App";
import { board, card, column, mockApi, region, settle, signIn, ticket } from "./helpers";

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

const OPEN = ticket({ id: 11, title: "Open one", status: "open", group: 2 });
const ACK = ticket({ id: 12, title: "Acked one", status: "acknowledged", group: 2 });
const PROG = ticket({ id: 13, title: "Doing one", status: "in_progress", group: 2 });
const DONE = ticket({ id: 14, title: "Done one", status: "done" });
const DASH = board({ todo: [OPEN, ACK], in_progress: [PROG], completed: [DONE] });

function form() {
  return region("New ticket");
}

describe("App: New ticket", () => {
  it("shows a New ticket panel with a heading and the inputs Title, Details, Priority and Due", async () => {
    mockApi();
    render(<App />);
    await signIn();
    const f = form();
    expect(f).toHaveClass("panel", "new-ticket");
    expect(within(f).getByRole("heading", { level: 2, name: /^New ticket/ })).toBeInTheDocument();
    expect(within(f).getByLabelText("Title")).toBeInTheDocument();
    expect(within(f).getByLabelText("Details")).toBeInTheDocument();
    expect(within(f).getByLabelText("Due")).toHaveAttribute("type", "date");
    const prio = within(f).getByLabelText("Priority") as HTMLSelectElement;
    expect(prio.tagName).toBe("SELECT");
    expect([...prio.options].map((o) => o.value)).toEqual(["low", "normal", "urgent"]);
    expect(prio.value).toBe("normal");
    expect(within(f).getByRole("button", { name: "File ticket" })).toBeInTheDocument();
  });

  it("File ticket posts the form to /api/tickets with the token", async () => {
    const api = mockApi();
    render(<App />);
    await signIn("tok-her");
    const f = form();
    fireEvent.change(within(f).getByLabelText("Title"), { target: { value: "Fix the gate" } });
    fireEvent.change(within(f).getByLabelText("Details"), { target: { value: "It squeaks" } });
    fireEvent.change(within(f).getByLabelText("Priority"), { target: { value: "urgent" } });
    fireEvent.change(within(f).getByLabelText("Due"), { target: { value: "2026-10-20" } });
    fireEvent.click(within(f).getByRole("button", { name: "File ticket" }));
    await settle();
    const posts = api.calls("POST /api/tickets");
    expect(posts).toHaveLength(1);
    expect(posts[0].headers["authorization"]).toBe("Bearer tok-her");
    expect(posts[0].body).toEqual({ title: "Fix the gate", details: "It squeaks", priority: "urgent", due: "2026-10-20" });
  });

  it("sends due as null when the Due field is empty", async () => {
    const api = mockApi();
    render(<App />);
    await signIn();
    fireEvent.change(within(form()).getByLabelText("Title"), { target: { value: "No date" } });
    fireEvent.click(within(form()).getByRole("button", { name: "File ticket" }));
    await settle();
    expect(api.calls("POST /api/tickets")[0].body).toEqual({ title: "No date", details: "", priority: "normal", due: null });
  });

  it("after filing, clears the form and reloads the board and the filed list", async () => {
    const api = mockApi();
    render(<App />);
    await signIn();
    expect(api.calls("GET /api/dashboard")).toHaveLength(1);
    fireEvent.change(within(form()).getByLabelText("Title"), { target: { value: "Fresh" } });
    fireEvent.change(within(form()).getByLabelText("Priority"), { target: { value: "low" } });
    fireEvent.click(within(form()).getByRole("button", { name: "File ticket" }));
    await settle();
    expect(api.calls("GET /api/dashboard")).toHaveLength(2);
    expect(api.calls("GET /api/filed")).toHaveLength(2);
    expect(within(form()).getByLabelText("Title")).toHaveValue("");
    expect(within(form()).getByLabelText("Priority")).toHaveValue("normal");
  });

  it("a refused ticket shows Something went wrong and keeps what was typed", async () => {
    mockApi({ "POST /api/tickets": { status: 400, body: { error: "invalid request" } } });
    render(<App />);
    await signIn();
    fireEvent.change(within(form()).getByLabelText("Title"), { target: { value: "Keep me" } });
    fireEvent.click(within(form()).getByRole("button", { name: "File ticket" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Something went wrong");
    expect(within(form()).getByLabelText("Title")).toHaveValue("Keep me");
  });
});

describe("App: moving tickets", () => {
  it("an open ticket in To Do has Acknowledge, an acknowledged one Start, an in-progress one Done", async () => {
    mockApi({ "GET /api/dashboard": { body: DASH } });
    render(<App />);
    await signIn();
    const open = card("Open one", column("My board", "To Do"));
    expect(within(open).getAllByRole("button").map((b) => b.textContent)).toEqual(["Acknowledge"]);
    const ack = card("Acked one", column("My board", "To Do"));
    expect(within(ack).getAllByRole("button").map((b) => b.textContent)).toEqual(["Start"]);
    const prog = card("Doing one", column("My board", "In Progress"));
    expect(within(prog).getAllByRole("button").map((b) => b.textContent)).toEqual(["Done"]);
    expect(within(card("Done one", column("My board", "Completed"))).queryAllByRole("button")).toHaveLength(0);
  });

  it.each([
    ["Open one", "Acknowledge", 11, "acknowledged"],
    ["Acked one", "Start", 12, "in_progress"],
    ["Doing one", "Done", 13, "done"],
  ])("%s: %s posts the move and reloads the board", async (title, button, id, status) => {
    const api = mockApi({ "GET /api/dashboard": { body: DASH } });
    render(<App />);
    await signIn("tok-him");
    api.routes["GET /api/dashboard"] = { body: board({ completed: [ticket({ title: "Moved", status: "done" })] }) };
    fireEvent.click(within(card(title, region("My board"))).getByRole("button", { name: button }));
    await settle();
    const [post] = api.calls("POST /api/tickets/:id/status");
    expect(post.path).toBe(`/api/tickets/${id}/status`);
    expect(post.body).toEqual({ status });
    expect(post.headers["authorization"]).toBe("Bearer tok-him");
    expect(api.calls("GET /api/dashboard")).toHaveLength(2);
    expect(card("Moved", column("My board", "Completed"))).toBeInTheDocument();
  });

  it("a refused move shows Something went wrong; a 401 shows Wrong token", async () => {
    const api = mockApi({ "GET /api/dashboard": { body: DASH },
                          "POST /api/tickets/:id/status": { status: 409, body: { error: "invalid transition" } } });
    render(<App />);
    await signIn();
    fireEvent.click(within(card("Open one", region("My board"))).getByRole("button", { name: "Acknowledge" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Something went wrong");
    api.routes["POST /api/tickets/:id/status"] = { status: 401, body: { error: "unauthorized" } };
    fireEvent.click(within(card("Doing one", region("My board"))).getByRole("button", { name: "Done" }));
    await settle();
    expect(screen.getByRole("alert")).toHaveTextContent("Wrong token");
  });
});
