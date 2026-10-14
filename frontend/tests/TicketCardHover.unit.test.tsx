import "@testing-library/jest-dom/vitest";
import { describe, it, expect, afterEach } from "vitest";
import { render, cleanup, screen, fireEvent } from "@testing-library/react";
import TicketCard from "../src/TicketCard";
import HoverCard from "../src/HoverCard";
import type { Ticket } from "../src/types";

afterEach(() => {
  cleanup();
});

describe("TicketCard hover card", () => {
  const baseTicket: Ticket = {
    id: 1,
    title: "Buy milk",
    details: "Get 2% milk, please.",
    priority: "normal",
    due: "2025-01-15",
    status: "open",
    filed_by: "her",
    assigned_to: "him",
    created_at: "2025-01-10T10:00:00Z",
    updated_at: "2025-01-10T10:00:00Z",
  };

  it("wraps the title in HoverCard with the ticket prop", () => {
    render(<TicketCard ticket={baseTicket} />);

    const span = document.querySelector("h3.card-title span") as HTMLElement | null;

    expect(span).not.toBeNull();
    expect(span?.className).toContain("hover-target");
  });

  it("shows the hover card on mouse enter over the title", () => {
    render(<TicketCard ticket={baseTicket} />);

    const span = document.querySelector("h3.card-title span") as HTMLElement;
    expect(span).not.toBeNull();

    fireEvent.mouseEnter(span!);

    const tooltip = screen.getByRole("tooltip", { name: /Get 2% milk, please/i });
    expect(tooltip).toBeInTheDocument();
  });

  it("hides the hover card on mouse leave from the title", () => {
    render(<TicketCard ticket={baseTicket} />);

    const span = document.querySelector("h3.card-title span") as HTMLElement;
    fireEvent.mouseEnter(span!);

    expect(screen.queryByRole("tooltip")).toBeInTheDocument();

    fireEvent.mouseLeave(span!);

    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  });

  it("shows the hover card on focus of the title", () => {
    render(<TicketCard ticket={baseTicket} />);

    const span = document.querySelector("h3.card-title span") as HTMLElement;
    expect(span).not.toBeNull();

    fireEvent.focus(span!);

    const tooltip = screen.getByRole("tooltip");
    expect(tooltip).toBeInTheDocument();
  });

  it("hides the hover card on blur from the title", () => {
    render(<TicketCard ticket={baseTicket} />);

    const span = document.querySelector("h3.card-title span") as HTMLElement;
    fireEvent.focus(span!);

    expect(screen.queryByRole("tooltip")).toBeInTheDocument();

    fireEvent.blur(span!);

    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  });

  it("shows ticket details in the hover card", () => {
    render(<TicketCard ticket={baseTicket} />);

    const span = document.querySelector("h3.card-title span") as HTMLElement;
    fireEvent.mouseEnter(span!);

    const tooltip = screen.getByRole("tooltip");
    expect(tooltip).toHaveTextContent(/Get 2% milk, please/i);
  });

  it("shows 'No details' when ticket details are empty or whitespace", () => {
    const ticketWithEmptyDetails: Ticket = {
      ...baseTicket,
      details: "   ",
    };

    render(<TicketCard ticket={ticketWithEmptyDetails} />);

    const span = document.querySelector("h3.card-title span") as HTMLElement;
    fireEvent.mouseEnter(span!);

    const tooltip = screen.getByRole("tooltip");
    expect(tooltip).toHaveTextContent(/No details/i);
  });

  it("shows filed_by in the hover card", () => {
    render(<TicketCard ticket={baseTicket} />);

    const span = document.querySelector("h3.card-title span") as HTMLElement;
    fireEvent.mouseEnter(span!);

    const tooltip = screen.getByRole("tooltip");
    expect(tooltip).toHaveTextContent(/Filed by her/i);
  });

  it("shows assigned_to in the hover card", () => {
    render(<TicketCard ticket={baseTicket} />);

    const span = document.querySelector("h3.card-title span") as HTMLElement;
    fireEvent.mouseEnter(span!);

    const tooltip = screen.getByRole("tooltip");
    expect(tooltip).toHaveTextContent(/Assigned to him/i);
  });

  it("shows created date in the hover card", () => {
    render(<TicketCard ticket={baseTicket} />);

    const span = document.querySelector("h3.card-title span") as HTMLElement;
    fireEvent.mouseEnter(span!);

    const tooltip = screen.getByRole("tooltip");
    expect(tooltip).toHaveTextContent(/Created 2025-01-10/i);
  });

  it("keeps the card article with correct class names", () => {
    render(<TicketCard ticket={baseTicket} />);

    const article = screen.getByRole("article", { name: /Buy milk/i });
    expect(article).toHaveClass("card");
    expect(article).not.toHaveClass("urgent");
  });

  it("adds urgent class when ticket group is 0", () => {
    const urgentTicket: Ticket = {
      ...baseTicket,
      group: 0,
    };

    render(<TicketCard ticket={urgentTicket} />);

    const article = screen.getByRole("article", { name: /Buy milk/i });
    expect(article).toHaveClass("card");
    expect(article).toHaveClass("urgent");
  });

  it("renders card-meta with priority badge", () => {
    render(<TicketCard ticket={baseTicket} />);

    expect(screen.getByText(/normal/i)).toBeInTheDocument();
    const badge = screen.getByText(/normal/i).closest("span") as HTMLElement;
    expect(badge?.className).toContain("badge");
    expect(badge?.className).toContain("priority-normal");
  });

  it("renders due date in card-meta when present", () => {
    render(<TicketCard ticket={baseTicket} />);

    expect(screen.getByText(/due 2025-01-15/i)).toBeInTheDocument();
    const dueSpan = screen.getByText(/due 2025-01-15/i).closest("span") as HTMLElement;
    expect(dueSpan?.className).toContain("due");
  });

  it("does not render due date when ticket has no due", () => {
    const ticketWithoutDue: Ticket = {
      ...baseTicket,
      due: null,
    };

    render(<TicketCard ticket={ticketWithoutDue} />);

    expect(screen.queryByText(/due/i)).not.toBeInTheDocument();
  });

  it("renders status pill with underscores replaced by spaces", () => {
    const inProgressTicket: Ticket = {
      ...baseTicket,
      status: "in_progress",
    };

    render(<TicketCard ticket={inProgressTicket} />);

    expect(screen.getByText(/in progress/i)).toBeInTheDocument();
    const pill = screen.getByText(/in progress/i).closest("span") as HTMLElement;
    expect(pill?.className).toContain("pill");
    expect(pill?.className).toContain("status-in_progress");
  });

  it("renders 'for {assigned_to}' in card-meta", () => {
    render(<TicketCard ticket={baseTicket} />);

    expect(screen.getByText(/for him/i)).toBeInTheDocument();
    const whoSpan = screen.getByText(/for him/i).closest("span") as HTMLElement;
    expect(whoSpan?.className).toContain("who");
  });

  it("renders card-actions with children when provided", () => {
    render(
      <TicketCard ticket={baseTicket}>
        <button>Close</button>
      </TicketCard>
    );

    expect(screen.getByRole("button", { name: /close/i })).toBeInTheDocument();
    const actionsDiv = screen.getByRole("button", { name: /close/i }).closest("div") as HTMLElement;
    expect(actionsDiv?.className).toContain("card-actions");
  });

  it("does not render card-actions when children is false", () => {
    render(<TicketCard ticket={baseTicket} children={false} />);

    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    const actionsDiv = document.querySelector(".card-actions");
    expect(actionsDiv).toBeNull();
  });

  it("does not render card-actions when children is null", () => {
    render(<TicketCard ticket={baseTicket} children={null as unknown as React.ReactNode} />);

    const actionsDiv = document.querySelector(".card-actions");
    expect(actionsDiv).toBeNull();
  });
});
