// GD-1h: frontend/src/TicketCard.tsx — one card per ticket, used everywhere on the page.
import "@testing-library/jest-dom/vitest";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import TicketCard from "../src/TicketCard";
import { card, ticket } from "./helpers";

afterEach(cleanup);

describe("TicketCard", () => {
  it("is an article with the class card, named by the ticket's title", () => {
    render(<TicketCard ticket={ticket({ title: "Fix the sink" })} />);
    const el = card("Fix the sink");
    expect(el.tagName).toBe("ARTICLE");
    expect(el).toHaveClass("card");
    expect(el).not.toHaveClass("urgent");
  });

  it("shows the title in an h3 with the class card-title", () => {
    render(<TicketCard ticket={ticket({ title: "Fix the sink" })} />);
    const h = screen.getByRole("heading", { level: 3, name: "Fix the sink" });
    expect(h).toHaveClass("card-title");
    expect(h.textContent).toBe("Fix the sink");
  });

  it("has the class urgent when the ticket's group is 0, and not for groups 1 and 2", () => {
    render(<>
      <TicketCard ticket={ticket({ title: "zero", group: 0 })} />
      <TicketCard ticket={ticket({ title: "one", group: 1 })} />
      <TicketCard ticket={ticket({ title: "two", group: 2 })} />
    </>);
    expect(card("zero")).toHaveClass("card", "urgent");
    expect(card("one")).not.toHaveClass("urgent");
    expect(card("two")).not.toHaveClass("urgent");
  });

  it("shows the priority in a badge with the class priority-<priority>", () => {
    render(<TicketCard ticket={ticket({ title: "T", priority: "urgent" })} />);
    const badge = within(card("T")).getByText("urgent");
    expect(badge).toHaveClass("badge", "priority-urgent");
    expect(badge.closest(".card-meta")).not.toBeNull();
  });

  it("shows the due date as 'due YYYY-MM-DD', and no due element without one", () => {
    render(<>
      <TicketCard ticket={ticket({ title: "dated", due: "2026-10-20" })} />
      <TicketCard ticket={ticket({ title: "undated", due: null })} />
    </>);
    expect(within(card("dated")).getByText("due 2026-10-20")).toHaveClass("due");
    expect(card("undated").querySelector(".due")).toBeNull();
  });

  it("shows the status in a pill with the class status-<status>, underscores as spaces", () => {
    render(<>
      <TicketCard ticket={ticket({ title: "a", status: "in_progress" })} />
      <TicketCard ticket={ticket({ title: "b", status: "acknowledged" })} />
    </>);
    expect(within(card("a")).getByText("in progress")).toHaveClass("pill", "status-in_progress");
    expect(within(card("b")).getByText("acknowledged")).toHaveClass("pill", "status-acknowledged");
  });

  it("shows who it is for from assigned_to", () => {
    render(<>
      <TicketCard ticket={ticket({ title: "a", assigned_to: "him" })} />
      <TicketCard ticket={ticket({ title: "b", assigned_to: "her" })} />
    </>);
    expect(within(card("a")).getByText("for him")).toHaveClass("who");
    expect(within(card("b")).getByText("for her")).toHaveClass("who");
  });

  it("puts its children in a card-actions element, and has none without children", () => {
    const onClick = vi.fn();
    render(<>
      <TicketCard ticket={ticket({ title: "with" })}><button onClick={onClick}>Acknowledge</button></TicketCard>
      <TicketCard ticket={ticket({ title: "without" })} />
    </>);
    const button = within(card("with")).getByRole("button", { name: "Acknowledge" });
    expect(button.parentElement).toHaveClass("card-actions");
    fireEvent.click(button);
    expect(onClick).toHaveBeenCalledTimes(1);
    expect(card("without").querySelector(".card-actions")).toBeNull();
  });

  it("renders ticket text as text, never as HTML", () => {
    render(<TicketCard ticket={ticket({ title: "<img src=x onerror=alert(1)>" })} />);
    expect(screen.getByText("<img src=x onerror=alert(1)>")).toBeInTheDocument();
    expect(document.querySelector("img")).toBeNull();
  });
});
