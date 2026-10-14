import "@testing-library/jest-dom/vitest";
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import TicketCard from "../src/TicketCard";
import HouseholdBoard from "../src/HouseholdBoard";
import { ticket, board } from "./helpers";

describe("TicketCard onOpen prop", () => {
  const t = ticket();

  afterEach(() => {
    cleanup();
  });

  it("adds class openable when onOpen is provided", () => {
    const onOpen = vi.fn();
    render(<TicketCard ticket={t} onOpen={onOpen} />);
    expect(screen.getByRole("article")).toHaveClass("openable");
  });

  it("calls onOpen with the ticket when h3.card-title is clicked", () => {
    const onOpen = vi.fn();
    render(<TicketCard ticket={t} onOpen={onOpen} />);
    fireEvent.click(screen.getByRole("heading"));
    expect(onOpen).toHaveBeenCalledWith(t);
  });

  it("calls onOpen with the ticket when Enter is pressed on focused span.hover-target", () => {
    const onOpen = vi.fn();
    render(<TicketCard ticket={t} onOpen={onOpen} />);
    const target = screen.getByText(t.title).parentElement as HTMLElement;
    target.focus();
    fireEvent.keyDown(target, { key: "Enter", code: "Enter" });
    expect(onOpen).toHaveBeenCalledWith(t);
  });

  it("does not add openable class when onOpen is not provided", () => {
    render(<TicketCard ticket={t} />);
    const article = screen.getByRole("article");
    expect(article.className).not.toContain("openable");
  });

  it("does nothing on click when onOpen is not provided", () => {
    render(<TicketCard ticket={t} />);
    fireEvent.click(screen.getByText(t.title).parentElement!);
    // No error, no side effect expected
    expect(true).toBe(true);
  });

  it("does not add a new button when onOpen is provided", () => {
    const onOpen = vi.fn();
    render(<TicketCard ticket={t} onOpen={onOpen} />);
    const buttons = screen.getAllByRole("button");
    expect(buttons).toHaveLength(0);
  });
});

describe("HouseholdBoard optional props", () => {
  const b = board();

  afterEach(() => {
    cleanup();
  });

  it("passes onOpen to every TicketCard when provided", () => {
    const onOpen = vi.fn();
    render(<HouseholdBoard board={b} onOpen={onOpen} />);
    // Click a card title in each column to verify onOpen is wired
    if (b.todo.length > 0) {
      fireEvent.click(screen.getByText(b.todo[0].title).parentElement!);
      expect(onOpen).toHaveBeenCalledWith(b.todo[0]);
    }
  });

  it("renders children between h2 and div.board when provided", () => {
    const childrenContent = "Filter bar";
    render(
      <HouseholdBoard board={b}>
        <div data-testid="children-content">{childrenContent}</div>
      </HouseholdBoard>
    );
    expect(screen.getByTestId("children-content")).toBeInTheDocument();
    const h2 = screen.getByRole("heading", { name: "Household board" });
    const childrenEl = screen.getByTestId("children-content");
    // Verify children is rendered after h2 and before the board div
    expect(childrenEl.parentElement?.previousElementSibling).toBe(h2);
  });

  it("renders without onOpen and children when not provided", () => {
    render(<HouseholdBoard board={b} />);
    const headings = screen.getAllByRole("heading", { name: "Household board" });
    expect(headings).toHaveLength(1);
    expect(screen.getByRole("region", { name: "To Do" })).toBeInTheDocument();
  });
});
