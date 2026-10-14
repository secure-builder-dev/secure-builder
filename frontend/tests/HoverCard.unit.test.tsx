import "@testing-library/jest-dom/vitest";
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import HoverCard from "../src/HoverCard";
import type { Ticket } from "../src/types";

describe("HoverCard", () => {
  const baseTicket: Ticket = {
    id: 1,
    title: "Buy milk",
    details: "Whole milk, preferably organic",
    priority: "normal",
    due: "2026-01-15",
    status: "open",
    filed_by: "her",
    assigned_to: "him",
    created_at: "2026-01-10T14:30:00Z",
    updated_at: "2026-01-10T14:30:00Z",
  };

  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("renders children inside a span with class hover-target and tabIndex 0", () => {
    const { container } = render(<HoverCard ticket={baseTicket}><span>Click me</span></HoverCard>);
    const target = container.querySelector(".hover-target");
    expect(target).toBeInTheDocument();
    expect(target).toHaveClass("hover-target");
    expect(target).toHaveAttribute("tabIndex", "0");
    expect(target.textContent).toBe("Click me");
  });

  it("shows tooltip on mouseenter with correct content", () => {
    const { container } = render(<HoverCard ticket={baseTicket}><span>Title</span></HoverCard>);
    const target = container.querySelector(".hover-target")!;
    fireEvent.mouseEnter(target);
    const tooltip = screen.getByRole("tooltip");
    expect(tooltip).toHaveClass("hover-card");
    expect(tooltip).toContainHTML("<p>Whole milk, preferably organic</p>");
    expect(tooltip).toContainHTML("<p>Filed by her</p>");
    expect(tooltip).toContainHTML("<p>Assigned to him</p>");
    expect(tooltip).toContainHTML("<p>Created 2026-01-10</p>");
  });

  it("hides tooltip on mouseleave", () => {
    const { container } = render(<HoverCard ticket={baseTicket}><span>Title</span></HoverCard>);
    const target = container.querySelector(".hover-target")!;
    fireEvent.mouseEnter(target);
    expect(screen.queryByRole("tooltip")).toBeInTheDocument();
    fireEvent.mouseLeave(target);
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  });

  it("shows tooltip on focus and hides on blur", () => {
    const { container } = render(<HoverCard ticket={baseTicket}><span>Title</span></HoverCard>);
    const target = container.querySelector(".hover-target")!;
    fireEvent.focus(target);
    expect(screen.getByRole("tooltip")).toBeInTheDocument();
    fireEvent.blur(target);
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  });

  it("shows 'No details' when details is empty", () => {
    const ticketWithEmptyDetails = { ...baseTicket, details: "" };
    const { container } = render(<HoverCard ticket={ticketWithEmptyDetails}><span>Title</span></HoverCard>);
    const target = container.querySelector(".hover-target")!;
    fireEvent.mouseEnter(target);
    const tooltip = screen.getByRole("tooltip");
    expect(tooltip).toContainHTML("<p>No details</p>");
  });

  it("shows 'No details' when details is whitespace only", () => {
    const ticketWithWhitespaceDetails = { ...baseTicket, details: "   \n\t   " };
    const { container } = render(<HoverCard ticket={ticketWithWhitespaceDetails}><span>Title</span></HoverCard>);
    const target = container.querySelector(".hover-target")!;
    fireEvent.mouseEnter(target);
    const tooltip = screen.getByRole("tooltip");
    expect(tooltip).toContainHTML("<p>No details</p>");
  });

  it("truncates created_at to first 10 characters", () => {
    const ticketWithLongDate = { ...baseTicket, created_at: "2026-12-25T23:59:59.999Z" };
    const { container } = render(<HoverCard ticket={ticketWithLongDate}><span>Title</span></HoverCard>);
    const target = container.querySelector(".hover-target")!;
    fireEvent.mouseEnter(target);
    const tooltip = screen.getByRole("tooltip");
    expect(tooltip).toContainHTML("<p>Created 2026-12-25</p>");
  });

  it("does not show tooltip initially", () => {
    render(<HoverCard ticket={baseTicket}><span>Title</span></HoverCard>);
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  });
});
