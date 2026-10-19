import React from "react";
import { render, fireEvent, waitFor, screen, cleanup } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import TicketDetail from "../src/TicketDetail";
import * as api from "../src/api";

// Helper to create a ticket object
function makeTicket(overrides = {}) {
  return {
    id: 1,
    title: "Sample Ticket",
    details: "Some details",
    priority: "normal" as const,
    due: null,
    status: "open" as const,
    filed_by: "her" as const,
    assigned_to: "him" as const,
    created_at: "2023-01-01T00:00:00Z",
    updated_at: "2023-01-01T00:00:00Z",
    ...overrides,
  };
}

// Helper to create comment objects
function makeComment(id, body) {
  return {
    id,
    ticket_id: 1,
    author: "her" as const,
    body,
    created_at: "2023-01-01T00:00:00Z",
  };
}

// Helper to create history events
function makeEvent(id, kind, actor = "her", from = null, to = null) {
  return {
    id,
    ticket_id: 1,
    actor,
    kind,
    from_status: from,
    to_status: to,
    at: "2023-01-01T00:00:00Z",
  };
}

afterEach(() => {
  vi.restoreAllMocks();
  cleanup();
});

/**
 * Clause 1: Rendering structure
 */
test("testTicketDetailRendersStructure", () => {
  const ticket = makeTicket();
  const onClose = vi.fn();
  render(
    <TicketDetail
      token="dummy-token"
      ticket={ticket}
      me="her"
      onClose={onClose}
    />
  );

  // Section with correct classes and aria-label
  const section = screen.getByRole("region", { name: /Ticket details/i });
  expect(section).toHaveClass("panel", "ticket-detail");

  // Title
  const title = screen.getByRole("heading", { level: 2, name: ticket.title });
  expect(title).toBeInTheDocument();

  // Details paragraph (only when not empty)
  const details = screen.getByText(ticket.details);
  expect(details).toHaveClass("detail-text");

  // Card meta spans – badge, due (if any), pill, who
  const badge = screen.getByText(ticket.priority);
  expect(badge).toHaveClass(`badge priority-${ticket.priority}`);

  const pill = screen.getByText(ticket.status.replace(/_/g, " "));
  expect(pill).toHaveClass(`pill status-${ticket.status}`);

  const who = screen.getByText(`for ${ticket.assigned_to}`);
  expect(who).toHaveClass("who");

  // Comments and History headings
  expect(screen.getByRole("heading", { level: 3, name: /Comments/i })).toBeInTheDocument();
  expect(screen.getByRole("heading", { level: 3, name: /History/i })).toBeInTheDocument();

  // Close button
  const closeBtn = screen.getByRole("button", { name: /Close details/i });
  expect(closeBtn).toHaveClass("close-detail");
  fireEvent.click(closeBtn);
  expect(onClose).toHaveBeenCalled();
});

/**
 * Clause 2: Fetch comments and history on mount and ticket.id change.
 */
test("testTicketDetailFetchesCommentsAndHistory", async () => {
  const ticket1 = makeTicket({ id: 1 });
  const ticket2 = makeTicket({ id: 2 });

  const commentsResp = { comments: [makeComment(1, "First comment")] };
  const historyResp = { events: [makeEvent(1, "filed")] };

  const fetchCommentsSpy = vi.spyOn(api, "fetchComments").mockResolvedValueOnce(commentsResp).mockResolvedValueOnce({ comments: [] });
  const fetchHistorySpy = vi.spyOn(api, "fetchHistory").mockResolvedValueOnce(historyResp).mockResolvedValueOnce({ events: [] });

  const { rerender } = render(
    <TicketDetail token="t" ticket={ticket1} me="her" onClose={() => {}} />
  );

  // Initial fetches
  await waitFor(() => expect(fetchCommentsSpy).toHaveBeenCalledWith("t", 1));
  await waitFor(() => expect(fetchHistorySpy).toHaveBeenCalledWith("t", 1));

  // Verify comments rendered
  expect(screen.getByText("First comment")).toBeInTheDocument();

  // Change ticket id
  rerender(<TicketDetail token="t" ticket={ticket2} me="her" onClose={() => {}} />);

  await waitFor(() => expect(fetchCommentsSpy).toHaveBeenCalledWith("t", 2));
  await waitFor(() => expect(fetchHistorySpy).toHaveBeenCalledWith("t", 2));

  // When fetch fails, component should show empty lists (CommentThread empty state)
  fetchCommentsSpy.mockRejectedValueOnce(new Error("boom"));
  fetchHistorySpy.mockRejectedValueOnce(new Error("boom"));
  rerender(<TicketDetail token="t" ticket={ticket1} me="her" onClose={() => {}} />);

  await waitFor(() => {
    // CommentThread empty state text
    expect(screen.getByText(/No comments yet/i)).toBeInTheDocument();
    // History empty state text
    expect(screen.getByText(/No history/i)).toBeInTheDocument();
  });
});

/**
 * Clause 3: Adding a comment – success and failure handling.
 */
test("testTicketDetailAddCommentSuccessAndFailure", async () => {
  const ticket = makeTicket();
  const initialComments = { comments: [] };
  const history = { events: [] };

  vi.spyOn(api, "fetchComments").mockResolvedValue(initialComments);
  vi.spyOn(api, "fetchHistory").mockResolvedValue(history);

  const addCommentSuccess = vi.spyOn(api, "addComment").mockResolvedValue({
    id: 99,
    ticket_id: ticket.id,
    author: "her",
    body: "New comment",
    created_at: "2023-01-01T00:00:00Z",
  });

  render(
    <TicketDetail token="tok" ticket={ticket} me="her" onClose={() => {}} />
  );

  // Type a comment and submit
  const textarea = screen.getByLabelText(/Comment/i);
  fireEvent.change(textarea, { target: { value: "New comment" } });
  const submitBtn = screen.getByRole("button", { name: /Add comment/i });
  fireEvent.click(submitBtn);

  await waitFor(() => expect(addCommentSuccess).toHaveBeenCalledWith("tok", ticket.id, "New comment"));

  // New comment should appear at end of list
  await waitFor(() => expect(screen.getByText("New comment")).toBeInTheDocument());

  // Failure case
  const addCommentFail = vi.spyOn(api, "addComment").mockRejectedValue(new Error("fail"));
  fireEvent.change(textarea, { target: { value: "Another" } });
  fireEvent.click(submitBtn);

  await waitFor(() => expect(addCommentFail).toHaveBeenCalled());

  // Error message should be displayed inside the panel
  const err = screen.getByRole("alert");
  expect(err).toHaveClass("error");
  expect(err).toHaveTextContent("Could not add the comment");

  // Ensure the failed comment is not added to the list
  const comments = screen.queryAllByText("Another");
  expect(comments.length).toBe(0);
});
