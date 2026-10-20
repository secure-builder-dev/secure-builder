// TO-4f: frontend/src/EditTicketForm.tsx and the edit workflow of frontend/src/TicketDetail.tsx
import "@testing-library/jest-dom/vitest";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import EditTicketForm from "../src/EditTicketForm";
import TicketDetail from "../src/TicketDetail";
import type { Ticket, User } from "../src/types";
import { event, mockApi, region, settle, ticket } from "./helpers";

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

const T = ticket({ id: 61, title: "Buy paint", details: "white, matte", priority: "low", due: "2026-11-01",
  status: "open", filed_by: "her", assigned_to: "him" });

function form() {
  return screen.getByRole("form", { name: "Edit ticket" });
}

function fields(f: HTMLElement = form()) {
  return {
    title: within(f).getByLabelText("Title") as HTMLInputElement,
    details: within(f).getByLabelText("Details") as HTMLTextAreaElement,
    priority: within(f).getByLabelText("Priority") as HTMLSelectElement,
    due: within(f).getByLabelText("Due") as HTMLInputElement,
  };
}

describe("EditTicketForm", () => {
  it("is a form.edit-ticket named Edit ticket", () => {
    render(<EditTicketForm ticket={T} onSave={() => {}} onCancel={() => {}} />);
    const f = form();
    expect(f.tagName).toBe("FORM");
    expect(f).toHaveClass("edit-ticket");
  });

  it("has the labelled fields Title, Details, Priority and Due filled from the ticket", () => {
    render(<EditTicketForm ticket={T} onSave={() => {}} onCancel={() => {}} />);
    const { title, details, priority, due } = fields();
    expect(title.value).toBe("Buy paint");
    expect(details.value).toBe("white, matte");
    expect(priority.tagName).toBe("SELECT");
    expect(priority.value).toBe("low");
    expect(Array.from(priority.options).map((o) => o.value)).toEqual(["low", "normal", "urgent"]);
    expect(due.tagName).toBe("INPUT");
    expect(due.type).toBe("date");
    expect(due.value).toBe("2026-11-01");
  });

  it("leaves Due empty for a ticket without a due date", () => {
    render(<EditTicketForm ticket={ticket({ title: "No date", due: null, priority: "urgent" })} onSave={() => {}} onCancel={() => {}} />);
    const { due, priority } = fields();
    expect(due.value).toBe("");
    expect(priority.value).toBe("urgent");
  });

  it("has a Save submit button and a Cancel button", () => {
    render(<EditTicketForm ticket={T} onSave={() => {}} onCancel={() => {}} />);
    expect(within(form()).getByRole("button", { name: "Save" })).toHaveAttribute("type", "submit");
    expect(within(form()).getByRole("button", { name: "Cancel" })).toBeInTheDocument();
  });

  it("Save unchanged calls onSave with all four fields from the ticket", () => {
    const onSave = vi.fn();
    render(<EditTicketForm ticket={T} onSave={onSave} onCancel={() => {}} />);
    fireEvent.click(within(form()).getByRole("button", { name: "Save" }));
    expect(onSave).toHaveBeenCalledTimes(1);
    expect(onSave).toHaveBeenCalledWith({ title: "Buy paint", details: "white, matte", priority: "low", due: "2026-11-01" });
  });

  it("Save calls onSave with the edited values", () => {
    const onSave = vi.fn();
    render(<EditTicketForm ticket={T} onSave={onSave} onCancel={() => {}} />);
    const { title, details, priority, due } = fields();
    fireEvent.change(title, { target: { value: "Buy blue paint" } });
    fireEvent.change(details, { target: { value: "two cans" } });
    fireEvent.change(priority, { target: { value: "urgent" } });
    fireEvent.change(due, { target: { value: "2026-11-15" } });
    fireEvent.click(within(form()).getByRole("button", { name: "Save" }));
    expect(onSave).toHaveBeenCalledTimes(1);
    expect(onSave).toHaveBeenCalledWith({ title: "Buy blue paint", details: "two cans", priority: "urgent", due: "2026-11-15" });
  });

  it("Save sends due null when the Due field is empty", () => {
    const onSave = vi.fn();
    render(<EditTicketForm ticket={T} onSave={onSave} onCancel={() => {}} />);
    fireEvent.change(fields().due, { target: { value: "" } });
    fireEvent.submit(form());
    expect(onSave).toHaveBeenCalledWith({ title: "Buy paint", details: "white, matte", priority: "low", due: null });
  });

  it("Cancel calls onCancel and not onSave", () => {
    const onSave = vi.fn();
    const onCancel = vi.fn();
    render(<EditTicketForm ticket={T} onSave={onSave} onCancel={onCancel} />);
    fireEvent.click(within(form()).getByRole("button", { name: "Cancel" }));
    expect(onCancel).toHaveBeenCalledTimes(1);
    expect(onSave).not.toHaveBeenCalled();
  });

  it("with error shows p.error with role alert holding that text, inside the form", () => {
    render(<EditTicketForm ticket={T} onSave={() => {}} onCancel={() => {}} error="Something broke" />);
    const alert = within(form()).getByRole("alert");
    expect(alert.tagName).toBe("P");
    expect(alert).toHaveClass("error");
    expect(alert.textContent).toBe("Something broke");
  });

  it("without error shows no alert", () => {
    render(<EditTicketForm ticket={T} onSave={() => {}} onCancel={() => {}} />);
    expect(screen.queryByRole("alert")).toBeNull();
  });
});

function panel() {
  return region("Ticket details");
}

function editButton() {
  return within(panel()).queryByRole("button", { name: "Edit" });
}

function show(t: Ticket, me: User | null, onSaved = vi.fn()) {
  render(<TicketDetail token="tok-e" ticket={t} me={me} onClose={() => {}} onSaved={onSaved} />);
  return onSaved;
}

describe("TicketDetail: Edit button", () => {
  it("shows Edit to the filer of an open ticket, after the card-meta", async () => {
    mockApi();
    show(T, "her");
    await settle();
    const btn = editButton();
    expect(btn).not.toBeNull();
    const meta = panel().querySelector(".card-meta") as HTMLElement;
    expect(meta.contains(btn)).toBe(false);
    expect(meta.compareDocumentPosition(btn!) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("shows Edit to the filer of an acknowledged ticket", async () => {
    mockApi();
    show(ticket({ ...T, id: 62, status: "acknowledged" }), "her");
    await settle();
    expect(editButton()).not.toBeNull();
  });

  it("shows no Edit past acknowledged", async () => {
    mockApi();
    for (const status of ["in_progress", "done", "closed"] as const) {
      show(ticket({ ...T, id: 63, status }), "her");
      await settle();
      expect(editButton()).toBeNull();
      cleanup();
    }
  });

  it("shows no Edit to the assignee, or with nobody signed in", async () => {
    mockApi();
    show(T, "him");
    await settle();
    expect(editButton()).toBeNull();
    cleanup();
    show(T, null);
    await settle();
    expect(editButton()).toBeNull();
  });

  it("Edit shows the Edit ticket form in the panel, filled from the ticket", async () => {
    mockApi();
    show(T, "her");
    await settle();
    expect(within(panel()).queryByRole("form", { name: "Edit ticket" })).toBeNull();
    fireEvent.click(editButton()!);
    const f = within(panel()).getByRole("form", { name: "Edit ticket" });
    expect(f).toHaveClass("edit-ticket");
    expect(fields(f).title.value).toBe("Buy paint");
  });
});

describe("TicketDetail: saving an edit", () => {
  const ANSWER = ticket({ ...T, title: "Buy blue paint", details: "two cans", priority: "urgent", due: null,
    updated_at: "2026-10-05T10:00:00+00:00" });

  it("Save PATCHes the four fields with the token, closes the form, shows the answer, refetches history, calls onSaved", async () => {
    let historyCalls = 0;
    const api = mockApi({
      "PATCH /api/tickets/:id": { body: ANSWER },
      "GET /api/tickets/:id/history": () => {
        historyCalls += 1;
        return { body: { events: historyCalls === 1
          ? [event({ ticket_id: 61, actor: "her", kind: "filed" })]
          : [event({ ticket_id: 61, actor: "her", kind: "filed" }), event({ ticket_id: 61, actor: "her", kind: "edited", to_status: null })] } };
      },
    });
    const onSaved = show(T, "her");
    await within(panel()).findByText("her filed it");
    const before = api.calls("GET /api/tickets/:id/history").length;
    fireEvent.click(editButton()!);
    const f = within(panel()).getByRole("form", { name: "Edit ticket" });
    const { title, details, priority, due } = fields(f);
    fireEvent.change(title, { target: { value: "Buy blue paint" } });
    fireEvent.change(details, { target: { value: "two cans" } });
    fireEvent.change(priority, { target: { value: "urgent" } });
    fireEvent.change(due, { target: { value: "" } });
    fireEvent.click(within(f).getByRole("button", { name: "Save" }));

    await waitFor(() => expect(onSaved).toHaveBeenCalledTimes(1));
    expect(onSaved).toHaveBeenCalledWith(ANSWER);
    const patches = api.calls("PATCH /api/tickets/:id");
    expect(patches).toHaveLength(1);
    expect(patches[0].path).toBe("/api/tickets/61");
    expect(patches[0].headers["authorization"]).toBe("Bearer tok-e");
    expect(patches[0].body).toEqual({ title: "Buy blue paint", details: "two cans", priority: "urgent", due: null });

    await waitFor(() => expect(within(panel()).queryByRole("form", { name: "Edit ticket" })).toBeNull());
    await waitFor(() => expect(api.calls("GET /api/tickets/:id/history").length).toBeGreaterThan(before));
    await within(panel()).findByText("her edited it");
  });

  it("after a successful save the panel shows the answered ticket", async () => {
    mockApi({ "PATCH /api/tickets/:id": { body: ANSWER } });
    show(T, "her");
    await settle();
    fireEvent.click(editButton()!);
    fireEvent.click(within(form()).getByRole("button", { name: "Save" }));
    await settle();
    const p = panel();
    expect(within(p).queryByRole("form", { name: "Edit ticket" })).toBeNull();
    expect(within(p).getByRole("heading", { level: 2, name: "Buy blue paint" })).toBeInTheDocument();
    expect(within(p).getByText("two cans")).toHaveClass("detail-text");
    const meta = p.querySelector(".card-meta") as HTMLElement;
    expect(within(meta).getByText("urgent")).toHaveClass("badge", "priority-urgent");
    expect(meta.querySelector(".due")).toBeNull();
  });

  it("a failed save keeps the form open with the error Could not save and calls no onSaved", async () => {
    mockApi({ "PATCH /api/tickets/:id": { status: 400, body: { error: "invalid request" } } });
    const onSaved = show(T, "her");
    await settle();
    fireEvent.click(editButton()!);
    fireEvent.change(fields().title, { target: { value: "Changed" } });
    fireEvent.click(within(form()).getByRole("button", { name: "Save" }));
    const alert = await within(panel()).findByRole("alert");
    expect(alert.textContent).toBe("Could not save");
    expect(alert).toHaveClass("error");
    expect(within(panel()).getByRole("form", { name: "Edit ticket" })).toBeInTheDocument();
    expect(onSaved).not.toHaveBeenCalled();
    expect(within(panel()).getByRole("heading", { level: 2, name: "Buy paint" })).toBeInTheDocument();
  });
});
