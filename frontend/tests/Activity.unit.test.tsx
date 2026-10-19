// Activity.unit.test.tsx – tests for CommentThread and HistoryList components
import "@testing-library/jest-dom/vitest";
import { describe, expect, test, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import CommentThread from "../src/CommentThread";
import HistoryList from "../src/HistoryList";

// Ensure each test runs with a clean DOM
afterEach(() => {
  cleanup();
});

describe("CommentThread component", () => {
  const sampleComments = [
    {
      id: 1,
      ticket_id: 42,
      author: "her" as const,
      body: "First comment",
      created_at: "2024-01-01T00:00:00Z",
    },
    {
      id: 2,
      ticket_id: 42,
      author: "him" as const,
      body: "Second comment",
      created_at: "2024-01-02T00:00:00Z",
    },
  ];

  test("test_comment_thread_renders_comments_and_empty_state", () => {
    // With comments
    render(<CommentThread comments={sampleComments} onAdd={() => {}} />);
    const container = screen.getByRole("region", { name: /comment thread/i }) ||
      screen.getByClass("comment-thread");
    expect(container).toHaveClass("comment-thread");
    const list = container.querySelector("ol.comments");
    expect(list).toBeInTheDocument();
    const items = list?.querySelectorAll("li.comment");
    expect(items?.length).toBe(sampleComments.length);
    // Verify form exists
    const form = container.querySelector("form.comment-form");
    expect(form).toBeInTheDocument();
    // Verify first comment content
    const first = items?.[0];
    expect(first?.querySelector("span.comment-author")).toHaveTextContent("her");
    expect(first?.querySelector("p.comment-body")).toHaveTextContent("First comment");

    // Without comments
    render(<CommentThread comments={[]} onAdd={() => {}} />);
    const emptyMsg = screen.getByText("No comments yet");
    expect(emptyMsg).toBeInTheDocument();
    expect(emptyMsg).toHaveClass("empty");
  });

  test("test_comment_thread_form_submission_and_blank_handling", () => {
    const onAdd = vi.fn();
    render(<CommentThread comments={[]} onAdd={onAdd} />);
    const textarea = screen.getByLabelText("Comment") as HTMLTextAreaElement;
    const button = screen.getByRole("button", { name: /add comment/i });

    // Submit non‑blank text with surrounding spaces
    fireEvent.change(textarea, { target: { value: "  hello world  " } });
    fireEvent.click(button);
    expect(onAdd).toHaveBeenCalledTimes(1);
    expect(onAdd).toHaveBeenCalledWith("hello world");
    expect(textarea.value).toBe("");

    // Submit blank (only spaces) – should not call onAdd
    onAdd.mockReset();
    fireEvent.change(textarea, { target: { value: "   " } });
    fireEvent.click(button);
    expect(onAdd).not.toHaveBeenCalled();
    expect(textarea.value).toBe("");
  });
});

describe("HistoryList component", () => {
  const sampleEvents = [
    {
      id: 1,
      ticket_id: 42,
      actor: "her" as const,
      kind: "filed" as const,
      from_status: null,
      to_status: "open" as const,
      at: "2024-01-01T00:00:00Z",
    },
    {
      id: 2,
      ticket_id: 42,
      actor: "him" as const,
      kind: "status" as const,
      from_status: "open",
      to_status: "acknowledged",
      at: "2024-01-02T00:00:00Z",
    },
    {
      id: 3,
      ticket_id: 42,
      actor: "her" as const,
      kind: "edited" as const,
      from_status: null,
      to_status: null,
      at: "2024-01-03T00:00:00Z",
    },
  ];

  test("test_history_list_renders_events_and_empty_state", () => {
    // With events
    render(<HistoryList events={sampleEvents} />);
    const list = screen.getByRole("list", { name: /history/i }) ||
      document.querySelector("ol.history");
    expect(list).toHaveClass("history");
    expect(list).toBeInTheDocument();
    const items = list?.querySelectorAll("li");
    expect(items?.length).toBe(sampleEvents.length);
    // Verify text content of each event (oldest first)
    expect(items?.[0]).toHaveTextContent("her filed it");
    expect(items?.[1]).toHaveTextContent("him moved it from open to acknowledged");
    expect(items?.[2]).toHaveTextContent("her edited it");

    // Without events
    render(<HistoryList events={[]} />);
    const emptyMsg = screen.getByText("No history");
    expect(emptyMsg).toBeInTheDocument();
    expect(emptyMsg).toHaveClass("empty");
  });
});
