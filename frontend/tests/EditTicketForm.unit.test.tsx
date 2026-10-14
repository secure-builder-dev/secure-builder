import "@testing-library/jest-dom/vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { vi } from "vitest";
import type { Ticket } from "../src/types";
import EditTicketForm from "../src/EditTicketForm";

const ticket: Ticket = {
  id: 1,
  title: "Buy milk",
  details: "Get 2%",
  priority: "normal",
  due: "2026-01-15",
  status: "open",
  filed_by: "her",
  assigned_to: "him",
  created_at: "2026-01-01T10:00:00Z",
  updated_at: "2026-01-01T10:00:00Z",
};

const onSave = vi.fn();
const onCancel = vi.fn();

function renderForm(t: Ticket = ticket, error?: string) {
  return render(
    <EditTicketForm ticket={t} onSave={onSave} onCancel={onCancel} error={error} />
  );
}

describe("EditTicketForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders form.edit-ticket with aria-label Edit ticket", () => {
    renderForm();
    const form = screen.getByRole("form", { name: /edit ticket/i });
    expect(form).toHaveClass("edit-ticket");
  });

  it("shows labelled field Title filled from the ticket", () => {
    renderForm();
    const input = screen.getByLabelText(/title/i);
    expect(input).toHaveValue(ticket.title);
  });

  it("shows labelled field Details filled from the ticket", () => {
    renderForm();
    const textarea = screen.getByLabelText(/details/i);
    expect(textarea).toHaveValue(ticket.details);
  });

  it("shows labelled field Priority as a select with low, normal, urgent options filled from the ticket", () => {
    renderForm();
    const select = screen.getByLabelText(/priority/i) as HTMLSelectElement;
    expect(select.value).toBe(ticket.priority);
    expect(Array.from(select.options).map((o) => o.value)).toEqual(["low", "normal", "urgent"]);
  });

  it("shows labelled field Due as a date input filled from the ticket", () => {
    renderForm();
    const input = screen.getByLabelText(/due/i) as HTMLInputElement;
    expect(input.type).toBe("date");
    expect(input.value).toBe(ticket.due);
  });

  it("shows a Save submit button", () => {
    renderForm();
    const saveBtn = screen.getByRole("button", { name: /save/i });
    expect(saveBtn).toBeInTheDocument();
    expect(saveBtn.tagName.toLowerCase()).toBe("button");
    expect(saveBtn.getAttribute("type")).toBe("submit");
  });

  it("shows a Cancel button that calls onCancel", () => {
    renderForm();
    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));
    expect(onCancel).toHaveBeenCalled();
  });

  it("Save calls onSave with all four fields", () => {
    renderForm();
    fireEvent.click(screen.getByRole("button", { name: /save/i }));
    expect(onSave).toHaveBeenCalledWith({
      title: ticket.title,
      details: ticket.details,
      priority: ticket.priority,
      due: ticket.due,
    });
  });

  it("Save calls onSave with due null when the field is empty", () => {
    const t = { ...ticket, due: null };
    renderForm(t);
    fireEvent.click(screen.getByRole("button", { name: /save/i }));
    expect(onSave).toHaveBeenCalledWith({
      title: t.title,
      details: t.details,
      priority: t.priority,
      due: null,
    });
  });

  it("with error the form shows p.error with role alert holding that text", () => {
    const err = "Something went wrong";
    renderForm(ticket, err);
    const alert = screen.getByRole("alert");
    expect(alert).toHaveClass("error");
    expect(alert).toHaveTextContent(err);
  });
});


