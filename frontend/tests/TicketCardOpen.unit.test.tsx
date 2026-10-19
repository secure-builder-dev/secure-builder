import "@testing-library/jest-dom/vitest";
import { render, fireEvent, screen, cleanup } from "@testing-library/react";
import TicketCard from "../src/TicketCard";
import HouseholdBoard from "../src/HouseholdBoard";
import type { Ticket, Board } from "../src/types";
import { describe, it, expect, vi, afterEach } from "vitest";

/**
 * Unit tests for the optional `onOpen` prop added to TicketCard and its propagation
 * through HouseholdBoard. These tests are written to fail against the current
 * implementation, which does not support the prop.
 */

describe("TicketCard onOpen behavior", () => {
  afterEach(() => {
    cleanup();
  });

  const ticket: Ticket = {
    id: 1,
    title: "Test ticket",
    details: "",
    priority: "normal",
    due: null,
    status: "open",
    filed_by: "her",
    assigned_to: "him",
    created_at: "2023-01-01T00:00:00Z",
    updated_at: "2023-01-01T00:00:00Z",
  };

  it("adds openable class and calls onOpen on click", () => {
    const onOpen = vi.fn();
    render(<TicketCard ticket={ticket} onOpen={onOpen} />);
    const article = screen.getByLabelText(ticket.title);
    expect(article).toHaveClass("openable");
    const title = screen.getByRole("heading", { name: ticket.title });
    fireEvent.click(title);
    expect(onOpen).toHaveBeenCalledTimes(1);
    expect(onOpen).toHaveBeenCalledWith(ticket);
  });

  it("calls onOpen on Enter key when hover target is focused", () => {
    const onOpen = vi.fn();
    render(<TicketCard ticket={ticket} onOpen={onOpen} />);
    const hoverTarget = document.querySelector("span.hover-target");
    if (!hoverTarget) throw new Error("hover target not found");
    hoverTarget.focus();
    fireEvent.keyDown(hoverTarget, { key: "Enter", code: "Enter" });
    expect(onOpen).toHaveBeenCalledTimes(1);
    expect(onOpen).toHaveBeenCalledWith(ticket);
  });

  it("without onOpen renders unchanged and no extra button", () => {
    const { container } = render(<TicketCard ticket={ticket} />);
    const article = screen.getByLabelText(ticket.title);
    expect(article).not.toHaveClass("openable");
    // No button should be rendered inside the card
    expect(container.querySelector("button")).toBeNull();
  });
});

describe("HouseholdBoard onOpen and children rendering", () => {
  afterEach(() => {
    cleanup();
  });

  const board: Board = {
    todo: [
      {
        id: 2,
        title: "Todo",
        details: "",
        priority: "low",
        due: null,
        status: "open",
        filed_by: "her",
        assigned_to: "him",
        created_at: "2023-01-01T00:00:00Z",
        updated_at: "2023-01-01T00:00:00Z",
      },
    ],
    in_progress: [],
    completed: [],
  };

  it("passes onOpen to each TicketCard", () => {
    const onOpen = vi.fn();
    render(<HouseholdBoard board={board} onOpen={onOpen} />);
    const title = screen.getByRole("heading", { name: "Todo" });
    fireEvent.click(title);
    expect(onOpen).toHaveBeenCalledTimes(1);
    expect(onOpen).toHaveBeenCalledWith(board.todo[0]);
  });

  it("renders children between h2 and board div", () => {
    render(
      <HouseholdBoard board={board}>
        <div data-testid="extra">Extra content</div>
      </HouseholdBoard>
    );
    const h2 = screen.getByRole("heading", { name: "Household board" });
    const extra = screen.getByTestId("extra");
    const boardDiv = document.querySelector("div.board");
    if (!boardDiv) throw new Error("board div not found");
    // Ensure ordering: h2 < extra < boardDiv
    expect(h2.compareDocumentPosition(extra)).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
    expect(extra.compareDocumentPosition(boardDiv)).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
  });
});
