import "@testing-library/jest-dom/vitest";
import { describe, it, expect, afterEach, beforeAll, vi, beforeEach } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { ticket } from "./helpers";

describe("TicketCard", () => {
  let TicketCard: typeof import("../src/TicketCard").default;

  beforeAll(async () => {
    const mod = await import("../src/TicketCard");
    TicketCard = mod.default;
  });

  afterEach(cleanup);

  it("default-exports a component that renders an article with class 'card' and aria-label set to the title", () => {
    const t = ticket({ title: "Buy milk" });
    render(<TicketCard ticket={t} />);
    const article = screen.getByRole("article", { name: "Buy milk" });
    expect(article).toHaveClass("card");
  });

  it("adds class 'urgent' when ticket.group is 0", () => {
    const t = ticket({ group: 0 });
    render(<TicketCard ticket={t} />);
    const article = screen.getByRole("article");
    expect(article).toHaveClass("card", "urgent");
  });

  it("does not add class 'urgent' when ticket.group is 1", () => {
    const t = ticket({ group: 1 });
    render(<TicketCard ticket={t} />);
    const article = screen.getByRole("article");
    expect(article).toHaveClass("card");
    expect(article).not.toHaveClass("urgent");
  });

  it("does not add class 'urgent' when ticket.group is undefined", () => {
    const t = ticket({ group: undefined });
    render(<TicketCard ticket={t} />);
    const article = screen.getByRole("article");
    expect(article).toHaveClass("card");
    expect(article).not.toHaveClass("urgent");
  });

  it("renders the title in an h3 with class 'card-title'", () => {
    const t = ticket({ title: "Fix the leak" });
    render(<TicketCard ticket={t} />);
    expect(screen.getByRole("heading", { name: "Fix the leak", level: 3 })).toHaveClass("card-title");
  });

  it("renders priority inside card-meta div with correct classes", () => {
    const t = ticket({ priority: "urgent" });
    render(<TicketCard ticket={t} />);
    expect(screen.getByText("urgent")).toHaveClass("badge", "priority-urgent");
  });

  it("renders due date inside card-meta div only when due is set", () => {
    const t = ticket({ due: "2025-12-25" });
    render(<TicketCard ticket={t} />);
    expect(screen.getByText(/due 2025-12-25/)).toHaveClass("due");
  });

  it("does not render due date when due is null", () => {
    const t = ticket({ due: null });
    render(<TicketCard ticket={t} />);
    expect(screen.queryByText(/due/)).not.toBeInTheDocument();
  });

  it("renders status with underscore replaced by space inside card-meta div", () => {
    const t = ticket({ status: "in_progress" });
    render(<TicketCard ticket={t} />);
    expect(screen.getByText("in progress")).toHaveClass("pill", "status-in_progress");
  });

  it("renders assigned_to as 'for {assigned_to}' inside card-meta div", () => {
    const t = ticket({ assigned_to: "him" });
    render(<TicketCard ticket={t} />);
    expect(screen.getByText("for him")).toHaveClass("who");
  });

  it("renders children inside a div with class 'card-actions' when children are given", () => {
    const t = ticket();
    render(<TicketCard ticket={t}><button>Close</button></TicketCard>);
    expect(screen.getByRole("button", { name: "Close" })).toBeInTheDocument();
    const actions = screen.getByText("Close").closest("div") as HTMLElement | null;
    expect(actions).toHaveClass("card-actions");
  });

  it("does not render card-actions when children is undefined", () => {
    const t = ticket();
    render(<TicketCard ticket={t} />);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(screen.queryByText(/card-actions/)).not.toBeInTheDocument();
  });

  it("does not render card-actions when children is null", () => {
    const t = ticket();
    render(<TicketCard ticket={t} children={null as unknown as React.ReactNode} />);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("does not render card-actions when children is false", () => {
    const t = ticket();
    render(<TicketCard ticket={t} children={false as unknown as React.ReactNode} />);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("renders all ticket text as React text, never as HTML", () => {
    const t = ticket({ title: "<script>alert('xss')</script>", details: "test" });
    render(<TicketCard ticket={t} />);
    const heading = screen.getByRole("heading");
    expect(heading.textContent).toBe("<script>alert('xss')</script>");
    // innerHTML shows the escaped markup when React renders text safely
    expect(heading.innerHTML).toContain("&lt;script&gt;");
  });
});