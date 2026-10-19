import "@testing-library/jest-dom/vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { describe, expect, test, vi, afterEach } from "vitest";

afterEach(() => {
  cleanup();
});

vi.mock("../src/HoverCard", () => ({
  default: () => null,
}));

import HoverCard from "../src/HoverCard";

type Ticket = {
  details: string;
  filed_by: "her" | "him";
  assigned_to: "her" | "him";
  created_at: string;
};

const mockTicket: Ticket = {
  details: "Some details",
  filed_by: "her",
  assigned_to: "him",
  created_at: "2023-08-15T12:34:56Z",
};

describe("HoverCard component", () => {
  test("rendersChildrenInHoverTargetSpan", () => {
    render(
      <HoverCard ticket={mockTicket}>
        <span data-testid="child">Child content</span>
      </HoverCard>
    );
    const span = screen.getByRole("button", { name: /child content/i })
      || screen.getByText("Child content");
    // The span should have class hover-target and tabIndex=0
    expect(span).toHaveClass("hover-target");
    expect(span).toHaveAttribute("tabindex", "0");
  });

  test("showsTooltipOnHoverAndFocus", async () => {
    render(
      <HoverCard ticket={mockTicket}>
        <span>Hover me</span>
      </HoverCard>
    );
    const target = screen.getByText("Hover me");
    // Tooltip should not be in the document initially
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
    // Mouse enter
    fireEvent.mouseEnter(target);
    const tooltip = await screen.findByRole("tooltip");
    expect(tooltip).toBeInTheDocument();
    // Mouse leave
    fireEvent.mouseLeave(target);
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
    // Focus
    fireEvent.focus(target);
    const tooltip2 = await screen.findByRole("tooltip");
    expect(tooltip2).toBeInTheDocument();
    // Blur
    fireEvent.blur(target);
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  });

  test("tooltipContainsTicketInfo", async () => {
    const ticketWithEmptyDetails = { ...mockTicket, details: "" };
    render(
      <HoverCard ticket={ticketWithEmptyDetails}>
        <span>Info</span>
      </HoverCard>
    );
    const target = screen.getByText("Info");
    fireEvent.mouseEnter(target);
    const tooltip = await screen.findByRole("tooltip");
    const paragraphs = tooltip.querySelectorAll("p");
    expect(paragraphs).toHaveLength(4);
    // Details paragraph (empty -> No details)
    expect(paragraphs[0]).toHaveTextContent("No details");
    // Filed by
    expect(paragraphs[1]).toHaveTextContent(`Filed by ${ticketWithEmptyDetails.filed_by}`);
    // Assigned to
    expect(paragraphs[2]).toHaveTextContent(`Assigned to ${ticketWithEmptyDetails.assigned_to}`);
    // Created (first 10 chars of created_at)
    const createdPrefix = ticketWithEmptyDetails.created_at.slice(0, 10);
    expect(paragraphs[3]).toHaveTextContent(`Created ${createdPrefix}`);
  });
});
