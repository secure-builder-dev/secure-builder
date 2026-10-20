// TO-3f: frontend/src/TicketCard.tsx (onOpen) and frontend/src/HouseholdBoard.tsx (onOpen, children).
import "@testing-library/jest-dom/vitest";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import TicketCard from "../src/TicketCard";
import HouseholdBoard from "../src/HouseholdBoard";
import { board, card, cards, column, region, ticket } from "./helpers";

afterEach(cleanup);

function title(el: HTMLElement) {
  return el.querySelector("h3.card-title") as HTMLElement;
}

function target(el: HTMLElement) {
  return el.querySelector("h3.card-title .hover-target") as HTMLElement;
}

describe("TicketCard with onOpen", () => {
  it("has the classes card and openable", () => {
    render(<TicketCard ticket={ticket({ title: "Fix the sink" })} onOpen={() => {}} />);
    expect(card("Fix the sink")).toHaveClass("card", "openable");
  });

  it("keeps the class urgent next to openable when the group is 0", () => {
    render(<TicketCard ticket={ticket({ title: "Hot", group: 0 })} onOpen={() => {}} />);
    expect(card("Hot")).toHaveClass("card", "urgent", "openable");
  });

  it("a click on the h3.card-title calls onOpen with the ticket", () => {
    const t = ticket({ title: "Fix the sink" });
    const onOpen = vi.fn();
    render(<TicketCard ticket={t} onOpen={onOpen} />);
    fireEvent.click(title(card("Fix the sink")));
    expect(onOpen).toHaveBeenCalledTimes(1);
    expect(onOpen).toHaveBeenCalledWith(t);
  });

  it("a click on the title text inside the hover target calls onOpen too", () => {
    const t = ticket({ title: "Fix the sink" });
    const onOpen = vi.fn();
    render(<TicketCard ticket={t} onOpen={onOpen} />);
    fireEvent.click(target(card("Fix the sink")));
    expect(onOpen).toHaveBeenCalledTimes(1);
    expect(onOpen).toHaveBeenCalledWith(t);
  });

  it("Enter while the title's span.hover-target has focus calls onOpen with the ticket", () => {
    const t = ticket({ title: "Fix the sink" });
    const onOpen = vi.fn();
    render(<TicketCard ticket={t} onOpen={onOpen} />);
    const span = target(card("Fix the sink"));
    expect(span).not.toBeNull();
    span.focus();
    expect(span).toHaveFocus();
    fireEvent.keyDown(span, { key: "Enter", code: "Enter" });
    expect(onOpen).toHaveBeenCalledTimes(1);
    expect(onOpen).toHaveBeenCalledWith(t);
  });

  it("another key on the hover target does not call onOpen", () => {
    const onOpen = vi.fn();
    render(<TicketCard ticket={ticket({ title: "Fix the sink" })} onOpen={onOpen} />);
    const span = target(card("Fix the sink"));
    span.focus();
    fireEvent.keyDown(span, { key: "x", code: "KeyX" });
    expect(onOpen).not.toHaveBeenCalled();
  });

  it("gets no new button", () => {
    render(<TicketCard ticket={ticket({ title: "Plain" })} onOpen={() => {}} />);
    expect(within(card("Plain")).queryAllByRole("button")).toHaveLength(0);
    expect(card("Plain").querySelector("button")).toBeNull();
  });

  it("with action buttons, the only buttons are those children", () => {
    render(
      <TicketCard ticket={ticket({ title: "Acts" })} onOpen={() => {}}>
        <button>Start</button>
      </TicketCard>,
    );
    const buttons = within(card("Acts")).getAllByRole("button");
    expect(buttons.map((b) => b.textContent)).toEqual(["Start"]);
  });
});

describe("TicketCard without onOpen", () => {
  it("has no openable class", () => {
    render(<TicketCard ticket={ticket({ title: "Fix the sink" })} />);
    expect(card("Fix the sink")).toHaveClass("card");
    expect(card("Fix the sink")).not.toHaveClass("openable");
  });

  it("a click on the title or Enter on it does nothing and adds no button", () => {
    render(<TicketCard ticket={ticket({ title: "Fix the sink" })} />);
    const el = card("Fix the sink");
    fireEvent.click(title(el));
    fireEvent.keyDown(target(el), { key: "Enter", code: "Enter" });
    expect(card("Fix the sink")).not.toHaveClass("openable");
    expect(within(el).queryAllByRole("button")).toHaveLength(0);
    expect(screen.getByRole("heading", { level: 3, name: "Fix the sink" })).toBeInTheDocument();
  });
});

const B = board({
  todo: [ticket({ title: "Todo one" }), ticket({ title: "Todo two", assigned_to: "him" })],
  in_progress: [ticket({ title: "Doing", status: "in_progress" })],
  completed: [ticket({ title: "Done", status: "done" })],
});

describe("HouseholdBoard with onOpen and children", () => {
  it("passes onOpen to every card it shows", () => {
    const onOpen = vi.fn();
    render(<HouseholdBoard board={B} onOpen={onOpen} />);
    const all = cards(region("Household board"));
    expect(all).toHaveLength(4);
    for (const el of all) expect(el).toHaveClass("openable");
    fireEvent.click(title(card("Todo two", column("Household board", "To Do"))));
    fireEvent.click(title(card("Doing", column("Household board", "In Progress"))));
    fireEvent.click(title(card("Done", column("Household board", "Completed"))));
    expect(onOpen.mock.calls.map((c) => c[0])).toEqual([B.todo[1], B.in_progress[0], B.completed[0]]);
  });

  it("without onOpen its cards are not openable", () => {
    render(<HouseholdBoard board={B} />);
    for (const el of cards(region("Household board"))) expect(el).not.toHaveClass("openable");
  });

  it("renders its children between its h2 and its div.board", () => {
    render(
      <HouseholdBoard board={B}>
        <p data-testid="extra">Filter goes here</p>
      </HouseholdBoard>,
    );
    const r = region("Household board");
    const h2 = within(r).getByRole("heading", { level: 2, name: "Household board" });
    const extra = within(r).getByTestId("extra");
    const grid = r.querySelector(".board") as HTMLElement;
    expect(grid).not.toBeNull();
    expect(grid.contains(extra)).toBe(false);
    expect(h2.contains(extra)).toBe(false);
    expect(h2.compareDocumentPosition(extra) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(extra.compareDocumentPosition(grid) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("without children it still shows the h2 and the board", () => {
    render(<HouseholdBoard board={B} />);
    const r = region("Household board");
    expect(within(r).getByRole("heading", { level: 2, name: "Household board" })).toBeInTheDocument();
    expect(r.querySelector(".board")).not.toBeNull();
  });
});
