// Unit tests for EditTicketForm and TicketDetail edit workflow
import "@testing-library/jest-dom/vitest";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";
import * as api from "../src/api";
import EditTicketForm from "../src/EditTicketForm";
import TicketDetail from "../src/TicketDetail";

afterEach(() => cleanup());

// Helper ticket object used in multiple tests
const baseTicket = {
  id: 1,
  title: "Fix sink",
  details: "Leaky faucet in kitchen",
  priority: "normal",
  due: "2024-12-31",
  status: "open",
  filed_by: "her",
  assigned_to: "him",
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-01T00:00:00Z",
};

describe("EditTicketForm component", () => {
  it("rendersEditTicketFormFields", () => {
    const onSave = vi.fn();
    const onCancel = vi.fn();
    render(
      <EditTicketForm ticket={baseTicket} onSave={onSave} onCancel={onCancel} />
    );

    const form = screen.getByRole("form", { name: /edit ticket/i });
    expect(form).toBeInTheDocument();
    expect(form).toHaveClass("edit-ticket");

    const titleInput = screen.getByLabelText(/title/i);
    expect(titleInput).toBeInTheDocument();
    expect(titleInput).toHaveValue(baseTicket.title);

    const detailsInput = screen.getByLabelText(/^details$/i);
    expect(detailsInput).toBeInTheDocument();
    expect(detailsInput).toHaveValue(baseTicket.details);

    const prioritySelect = screen.getByLabelText(/priority/i);
    expect(prioritySelect).toBeInTheDocument();
    expect(prioritySelect).toHaveValue(baseTicket.priority);

    const dueInput = screen.getByLabelText(/due/i);
    expect(dueInput).toBeInTheDocument();
    expect(dueInput).toHaveValue(baseTicket.due);

    expect(screen.getByRole("button", { name: /save/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /cancel/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it("editTicketFormSaveCallsOnSaveAndShowsError", async () => {
    const onSave = vi.fn();
    const onCancel = vi.fn();
    const errorMsg = "Network error";
    render(
      <EditTicketForm ticket={baseTicket} onSave={onSave} onCancel={onCancel} error={errorMsg} />
    );

    const errorParagraph = screen.getByRole("alert");
    expect(errorParagraph).toBeInTheDocument();
    expect(errorParagraph).toHaveClass("error");
    expect(errorParagraph).toHaveTextContent(errorMsg);

    const newTitle = "Fix bathtub";
    const newDetails = "Cracked porcelain";
    const newPriority = "urgent";
    const newDue = ""; // empty means null

    fireEvent.change(screen.getByLabelText(/^title$/i), { target: { value: newTitle } });
    fireEvent.change(screen.getByLabelText(/^details$/i), { target: { value: newDetails } });
    fireEvent.change(screen.getByLabelText(/^priority$/i), { target: { value: newPriority } });
    fireEvent.change(screen.getByLabelText(/^due$/i), { target: { value: newDue } });

    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() => {
      expect(onSave).toHaveBeenCalledTimes(1);
    });
    const calledArg = onSave.mock.calls[0][0];
    expect(calledArg.title).toBe(newTitle);
    expect(calledArg.details).toBe(newDetails);
    expect(calledArg.priority).toBe(newPriority);
    expect(calledArg.due).toBeNull();
  });
});

describe("TicketDetail edit workflow", () => {
  const mockEditTicket = vi.spyOn(api, "editTicket");
  const mockFetchHistory = vi.spyOn(api, "fetchHistory");

  beforeEach(() => {
    mockEditTicket.mockReset();
    mockFetchHistory.mockReset();
  });

  it("shows Edit button only for filer with open/acknowledged status and handles successful save", async () => {
    const onClose = vi.fn();
    const onSaved = vi.fn();
    const token = "dummy-token";
    const ticket = { ...baseTicket, status: "open", filed_by: "her" };

    const updatedTicket = { ...ticket, title: "Updated title", details: "Updated details", priority: "low", due: null };
    mockEditTicket.mockResolvedValue(updatedTicket);
    mockFetchHistory.mockResolvedValue({ events: [] });

    render(
      <TicketDetail token={token} ticket={ticket} me="her" onClose={onClose} onSaved={onSaved} />
    );

    const editBtn = screen.getByRole("button", { name: /edit/i });
    expect(editBtn).toBeInTheDocument();

    fireEvent.click(editBtn);
    const form = await screen.findByRole("form", { name: /edit ticket/i });
    expect(form).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/^title$/i), { target: { value: "Updated title" } });
    fireEvent.change(screen.getByLabelText(/^details$/i), { target: { value: "Updated details" } });
    fireEvent.change(screen.getByLabelText(/^priority$/i), { target: { value: "low" } });
    fireEvent.change(screen.getByLabelText(/^due$/i), { target: { value: "" } });

    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() => expect(mockEditTicket).toHaveBeenCalledTimes(1));
    expect(mockEditTicket).toHaveBeenCalledWith(token, ticket.id, {
      title: "Updated title",
      details: "Updated details",
      priority: "low",
      due: null,
    });

    await waitFor(() => {
      expect(screen.queryByRole("form", { name: /edit ticket/i })).not.toBeInTheDocument();
    });

    expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent("Updated title");

    await waitFor(() => expect(mockFetchHistory).toHaveBeenCalledTimes(2));

    expect(onSaved).toHaveBeenCalledWith(updatedTicket);
  });

  it("keeps form open and shows error on failed save", async () => {
    const onClose = vi.fn();
    const onSaved = vi.fn();
    const token = "dummy-token";
    const ticket = { ...baseTicket, status: "open", filed_by: "her" };

    mockEditTicket.mockRejectedValue(new Error("500"));

    render(
      <TicketDetail token={token} ticket={ticket} me="her" onClose={onClose} onSaved={onSaved} />
    );

    fireEvent.click(screen.getByRole("button", { name: /edit/i }));
    await screen.findByRole("form", { name: /edit ticket/i });

    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    const err = await screen.findByRole("alert");
    expect(err).toBeInTheDocument();
    expect(err).toHaveClass("error");
    expect(err).toHaveTextContent("Could not save");

    expect(screen.getByRole("form", { name: /edit ticket/i })).toBeInTheDocument();
    expect(onSaved).not.toHaveBeenCalled();
  });
});
