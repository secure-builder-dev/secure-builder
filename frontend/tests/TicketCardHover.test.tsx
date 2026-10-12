// GD-2b: frontend/src/TicketCard.tsx wraps its title in HoverCard, so every card on the page has a hover card.
import "@testing-library/jest-dom/vitest";
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import TicketCard from "../src/TicketCard";
import { card, ticket } from "./helpers";

afterEach(cleanup);

describe("TicketCard with a hover card", () => {
  it("wraps the title in a .hover-target inside the .card-title heading", () => {
    render(<TicketCard ticket={ticket({ title: "Fix the sink" })} />);
    const h = screen.getByRole("heading", { level: 3, name: "Fix the sink" });
    const span = h.querySelector(".hover-target");
    expect(span).not.toBeNull();
    expect(span!.textContent).toBe("Fix the sink");
  });

  it("hovering the title shows the ticket's details in a tooltip inside the card", () => {
    render(<>
      <TicketCard ticket={ticket({ title: "A", details: "about A", filed_by: "him", assigned_to: "her" })} />
      <TicketCard ticket={ticket({ title: "B", details: "about B" })} />
    </>);
    const a = card("A");
    fireEvent.mouseEnter(a.querySelector(".hover-target")!);
    const tip = within(a).getByRole("tooltip");
    expect(within(tip).getByText("about A")).toBeInTheDocument();
    expect(within(tip).getByText("Filed by him")).toBeInTheDocument();
    expect(screen.getAllByRole("tooltip")).toHaveLength(1);
    expect(screen.queryByText("about B")).toBeNull();
  });

  it("focusing the title shows the tooltip, and blur hides it", () => {
    render(<TicketCard ticket={ticket({ title: "A", details: "" })} />);
    const span = card("A").querySelector(".hover-target")!;
    fireEvent.focus(span);
    expect(within(screen.getByRole("tooltip")).getByText("No details")).toBeInTheDocument();
    fireEvent.blur(span);
    expect(screen.queryByRole("tooltip")).toBeNull();
  });

  it("keeps the card named by its title while the tooltip is shown", () => {
    render(<TicketCard ticket={ticket({ title: "Named", details: "long text" })} />);
    fireEvent.mouseEnter(card("Named").querySelector(".hover-target")!);
    expect(card("Named")).toHaveClass("card");
  });
});
