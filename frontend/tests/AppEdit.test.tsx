// E4: frontend/src/App.tsx — editing a ticket from the Ticket details panel.
import "@testing-library/jest-dom/vitest";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import App from "../src/App";
import { board, card, mockApi, region, settle, signIn, ticket } from "./helpers";

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

// signed in as her (the default /api/me answer)
const MINE_OPEN = ticket({ id: 31, title: "Buy paint", details: "white", priority: "low", due: "2026-11-01",
  filed_by: "her", assigned_to: "him", status: "open" });
const MINE_ACK = ticket({ id: 32, title: "Fix gate", filed_by: "her", assigned_to: "him", status: "acknowledged" });
const MINE_PROG = ticket({ id: 33, title: "Hang shelf", filed_by: "her", assigned_to: "him", status: "in_progress" });
const HIS = ticket({ id: 34, title: "Mow lawn", filed_by: "him", assigned_to: "her", status: "open", group: 2 });

function api(over = {}) {
  return mockApi({
    "GET /api/dashboard": { body: board({ todo: [HIS] }) },
    "GET /api/filed": { body: { tickets: [MINE_OPEN, MINE_ACK, MINE_PROG] } },
    "GET /api/board": { body: board({ todo: [MINE_OPEN, MINE_ACK, HIS], in_progress: [MINE_PROG] }) },
    ...over,
  });
}

async function open(title: string, inside: HTMLElement = region("Tickets I filed")) {
  fireEvent.click(card(title, inside).querySelector(".card-title")!);
  await settle();
}

function panel() {
  return region("Ticket details");
}

function editButton() {
  return within(panel()).queryByRole("button", { name: "Edit" });
}

describe("App: editing a ticket", () => {
  it("shows Edit only to the filer of an open or acknowledged ticket", async () => {
    api();
    render(<App />);
    await signIn();
    await open("Buy paint");
    expect(editButton()).not.toBeNull();
    await open("Fix gate");
    expect(editButton()).not.toBeNull();
    await open("Hang shelf");
    expect(editButton()).toBeNull();
    await open("Mow lawn", region("My board"));
    expect(editButton()).toBeNull();
  });

  it("Edit shows the Edit ticket form filled from the ticket", async () => {
    api();
    render(<App />);
    await signIn();
    await open("Buy paint");
    fireEvent.click(editButton()!);
    const form = within(panel()).getByRole("form", { name: "Edit ticket" });
    expect(form).toHaveClass("edit-ticket");
    expect((within(form).getByLabelText("Title") as HTMLInputElement).value).toBe("Buy paint");
    expect((within(form).getByLabelText("Details") as HTMLTextAreaElement).value).toBe("white");
    expect((within(form).getByLabelText("Priority") as HTMLSelectElement).value).toBe("low");
    expect((within(form).getByLabelText("Due") as HTMLInputElement).value).toBe("2026-11-01");
  });

  it("Save sends a PATCH with all four fields, then shows the answer, closes the form and re-fetches", async () => {
    const saved = { ...MINE_OPEN, title: "Buy blue paint", priority: "urgent" as const, due: null };
    const calls = api({ "PATCH /api/tickets/:id": { body: saved } });
    render(<App />);
    await signIn("tok-her");
    await open("Buy paint");
    const before = { dash: calls.calls("GET /api/dashboard").length, filed: calls.calls("GET /api/filed").length,
      board: calls.calls("GET /api/board").length, hist: calls.calls("GET /api/tickets/:id/history").length,
      sum: calls.calls("GET /api/summary").length };
    fireEvent.click(editButton()!);
    const form = within(panel()).getByRole("form", { name: "Edit ticket" });
    fireEvent.change(within(form).getByLabelText("Title"), { target: { value: "Buy blue paint" } });
    fireEvent.change(within(form).getByLabelText("Priority"), { target: { value: "urgent" } });
    fireEvent.change(within(form).getByLabelText("Due"), { target: { value: "" } });
    fireEvent.click(within(form).getByRole("button", { name: "Save" }));
    await settle();
    const patches = calls.calls("PATCH /api/tickets/:id");
    expect(patches).toHaveLength(1);
    expect(patches[0].path).toBe("/api/tickets/31");
    expect(patches[0].headers["authorization"]).toBe("Bearer tok-her");
    expect(patches[0].body).toEqual({ title: "Buy blue paint", details: "white", priority: "urgent", due: null });
    expect(within(panel()).queryByRole("form", { name: "Edit ticket" })).toBeNull();
    expect(within(panel()).getByRole("heading", { level: 2 }).textContent).toBe("Buy blue paint");
    expect(panel().querySelector(".badge.priority-urgent")).not.toBeNull();
    expect(calls.calls("GET /api/tickets/:id/history").length).toBe(before.hist + 1);
    expect(calls.calls("GET /api/dashboard").length).toBeGreaterThan(before.dash);
    expect(calls.calls("GET /api/filed").length).toBeGreaterThan(before.filed);
    expect(calls.calls("GET /api/board").length).toBeGreaterThan(before.board);
    expect(calls.calls("GET /api/summary").length).toBeGreaterThan(before.sum);
  });

  it("Cancel closes the form without saving", async () => {
    const calls = api();
    render(<App />);
    await signIn();
    await open("Buy paint");
    fireEvent.click(editButton()!);
    fireEvent.click(within(panel()).getByRole("button", { name: "Cancel" }));
    expect(within(panel()).queryByRole("form", { name: "Edit ticket" })).toBeNull();
    expect(calls.calls("PATCH /api/tickets/:id")).toHaveLength(0);
  });

  it("a failed save keeps the form open with the error Could not save", async () => {
    api({ "PATCH /api/tickets/:id": { status: 409, body: { error: "not editable" } } });
    render(<App />);
    await signIn();
    await open("Buy paint");
    fireEvent.click(editButton()!);
    const form = within(panel()).getByRole("form", { name: "Edit ticket" });
    fireEvent.change(within(form).getByLabelText("Title"), { target: { value: "Changed" } });
    fireEvent.click(within(form).getByRole("button", { name: "Save" }));
    await settle();
    const still = within(panel()).getByRole("form", { name: "Edit ticket" });
    expect(within(still).getByRole("alert").textContent).toBe("Could not save");
    expect(within(panel()).getByRole("heading", { level: 2 }).textContent).toBe("Buy paint");
    expect(screen.getAllByRole("alert")).toHaveLength(1);
  });
});
