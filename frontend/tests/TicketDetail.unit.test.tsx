import "@testing-library/jest-dom/vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, it, expect, beforeEach, vi } from "vitest";
import type { Ticket, User } from "../src/types";
import { settle } from "./helpers";
import TicketDetail from "../src/TicketDetail";

const mockTicket: Ticket = {
  id: 1,
  title: "Buy milk",
  details: "Get 2% milk, please.",
  priority: "normal",
  due: "2026-01-15",
  status: "open",
  filed_by: "her",
  assigned_to: "him",
  created_at: "2026-01-01T10:00:00Z",
  updated_at: "2026-01-01T10:00:00Z",
};

const mockToken = "mock-token";
const mockMe: User = "her";

vi.mock("../src/api", async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...(actual as any),
    fetchComments: vi.fn(),
    fetchHistory: vi.fn(),
    addComment: vi.fn(),
  };
});

const { fetchComments, fetchHistory, addComment } = await import("../src/api");

describe("TicketDetail", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("clause-1: renders section.panel.ticket-detail with h2 title, p.detail-text, div.card-meta, Comments h3, History h3, and Close details button", () => {
    const onClose = vi.fn();
    (fetchComments as any).mockResolvedValue({ comments: [] });
    (fetchHistory as any).mockResolvedValue({ events: [] });

    render(
      <TicketDetail
        token={mockToken}
        ticket={mockTicket}
        me={mockMe}
        onClose={onClose}
      />
    );

    expect(screen.getByRole("region", { name: "Ticket details" })).toHaveClass("panel", "ticket-detail");
    expect(screen.getByRole("heading", { name: "Buy milk", level: 2 })).toBeInTheDocument();
    expect(screen.getByText("Get 2% milk, please.")).toHaveClass("detail-text");
    expect(screen.getByText("normal")).toHaveClass("badge", "priority-normal");
    expect(screen.getByText("due 2026-01-15")).toHaveClass("due");
    expect(screen.getByText("open")).toHaveClass("pill", "status-open");
    expect(screen.getByText("for him")).toHaveClass("who");
    expect(screen.getByRole("heading", { name: "Comments", level: 3 })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "History", level: 3 })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Close details" })).toHaveClass("close-detail");
  });

  it("clause-1b: p.detail-text is not rendered when details are empty", () => {
    const ticketNoDetails = { ...mockTicket, details: "" };
    const onClose = vi.fn();
    (fetchComments as any).mockResolvedValue({ comments: [] });
    (fetchHistory as any).mockResolvedValue({ events: [] });

    render(
      <TicketDetail
        token={mockToken}
        ticket={ticketNoDetails}
        me={mockMe}
        onClose={onClose}
      />
    );

    expect(screen.queryByText(ticketNoDetails.details)).not.toBeInTheDocument();
    expect(screen.queryByRole("paragraph", { name: "" })).not.toBeInTheDocument();
  });

  it("clause-1c: Close details button calls onClose", async () => {
    const onClose = vi.fn();
    (fetchComments as any).mockResolvedValue({ comments: [] });
    (fetchHistory as any).mockResolvedValue({ events: [] });

    render(
      <TicketDetail
        token={mockToken}
        ticket={mockTicket}
        me={mockMe}
        onClose={onClose}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "Close details" }));
    expect(onClose).toHaveBeenCalled();
  });

  it("clause-2: fetches comments and history when it opens", async () => {
    const onClose = vi.fn();
    (fetchComments as any).mockResolvedValue({ comments: [] });
    (fetchHistory as any).mockResolvedValue({ events: [] });

    render(
      <TicketDetail
        token={mockToken}
        ticket={mockTicket}
        me={mockMe}
        onClose={onClose}
      />
    );

    await waitFor(() => {
      expect(fetchComments).toHaveBeenCalledWith(mockToken, mockTicket.id);
      expect(fetchHistory).toHaveBeenCalledWith(mockToken, mockTicket.id);
    });
  });

  it("clause-2b: fetches comments and history again when ticket.id changes", async () => {
    const onClose = vi.fn();
    const ticket2 = { ...mockTicket, id: 2, title: "Buy eggs" };
    (fetchComments as any).mockResolvedValue({ comments: [] });
    (fetchHistory as any).mockResolvedValue({ events: [] });

    const { rerender } = render(
      <TicketDetail
        token={mockToken}
        ticket={mockTicket}
        me={mockMe}
        onClose={onClose}
      />
    );

    await waitFor(() => {
      expect(fetchComments).toHaveBeenCalledWith(mockToken, mockTicket.id);
      expect(fetchHistory).toHaveBeenCalledWith(mockToken, mockTicket.id);
    });

    vi.clearAllMocks();
    rerender(
      <TicketDetail
        token={mockToken}
        ticket={ticket2}
        me={mockMe}
        onClose={onClose}
      />
    );

    await waitFor(() => {
      expect(fetchComments).toHaveBeenCalledWith(mockToken, ticket2.id);
      expect(fetchHistory).toHaveBeenCalledWith(mockToken, ticket2.id);
    });
  });

  it("clause-2c: failed comments answer leaves list empty while rest of panel works", async () => {
    const onClose = vi.fn();
    (fetchComments as any).mockRejectedValue(new Error("401"));
    (fetchHistory as any).mockResolvedValue({ events: [] });

    render(
      <TicketDetail
        token={mockToken}
        ticket={mockTicket}
        me={mockMe}
        onClose={onClose}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("No comments yet")).toBeInTheDocument();
    });
    expect(screen.getByRole("heading", { name: "Buy milk", level: 2 })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Close details" })).toBeInTheDocument();
  });

  it("clause-2d: failed history answer leaves list empty while rest of panel works", async () => {
    const onClose = vi.fn();
    (fetchComments as any).mockResolvedValue({ comments: [] });
    (fetchHistory as any).mockRejectedValue(new Error("401"));

    render(
      <TicketDetail
        token={mockToken}
        ticket={mockTicket}
        me={mockMe}
        onClose={onClose}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("No history")).toBeInTheDocument();
    });
    expect(screen.getByRole("heading", { name: "Buy milk", level: 2 })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Close details" })).toBeInTheDocument();
  });

  it("clause-3: adding a comment POSTs it and shows the answered comment at the end of the list", async () => {
    const onClose = vi.fn();
    const newComment = {
      id: 1,
      ticket_id: mockTicket.id,
      author: "her",
      body: "Great idea!",
      created_at: "2026-01-02T10:00:00Z",
    };
    (fetchComments as any).mockResolvedValue({ comments: [] });
    (fetchHistory as any).mockResolvedValue({ events: [] });
    (addComment as any).mockResolvedValue(newComment);

    render(
      <TicketDetail
        token={mockToken}
        ticket={mockTicket}
        me={mockMe}
        onClose={onClose}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("No comments yet")).toBeInTheDocument();
    });

    const textarea = screen.getByLabelText(/comment/i);
    fireEvent.change(textarea, { target: { value: "Great idea!" } });
    fireEvent.click(screen.getByRole("button", { name: /add comment/i }));
    await settle();

    await waitFor(() => {
      expect(addComment).toHaveBeenCalledWith(mockToken, mockTicket.id, "Great idea!");
    });

    await waitFor(() => {
      expect(screen.getByText("Great idea!")).toBeInTheDocument();
    });
  });

  it("clause-3b: failed POST shows p.error with role alert reading Could not add the comment and adds nothing", async () => {
    const onClose = vi.fn();
    (fetchComments as any).mockResolvedValue({ comments: [] });
    (fetchHistory as any).mockResolvedValue({ events: [] });
    (addComment as any).mockRejectedValue(new Error("400"));

    render(
      <TicketDetail
        token={mockToken}
        ticket={mockTicket}
        me={mockMe}
        onClose={onClose}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("No comments yet")).toBeInTheDocument();
    });

    const textarea = screen.getByLabelText(/comment/i);
    fireEvent.change(textarea, { target: { value: "Test comment" } });
    fireEvent.click(screen.getByRole("button", { name: /add comment/i }));
    await settle();

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Could not add the comment");
    });

    expect(screen.queryByText("Test comment")).not.toBeInTheDocument();
  });
});
