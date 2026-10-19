import "@testing-library/jest-dom/vitest";
import { render, cleanup } from "@testing-library/react";
import { afterEach, expect, test } from "vitest";
import TicketCard from "../src/TicketCard";

type Ticket = {
  id: number;
  title: string;
  details: string;
  priority: "low" | "normal" | "urgent";
  due: string | null;
  status: "open" | "acknowledged" | "in_progress" | "done" | "closed";
  filed_by: "her" | "him";
  assigned_to: "her" | "him";
  created_at: string;
  updated_at: string;
  group?: 0 | 1 | 2;
};

const baseTicket: Ticket = {
  id: 1,
  title: "Test Ticket",
  details: "",
  priority: "normal",
  due: null,
  status: "open",
  filed_by: "her",
  assigned_to: "him",
  created_at: "2023-01-01T00:00:00Z",
  updated_at: "2023-01-01T00:00:00Z",
};

afterEach(() => {
  cleanup();
});

test("renders article with correct classes and aria-label", () => {
  const { container } = render(<TicketCard ticket={{ ...baseTicket, group: 0 }} />);
  const article = container.querySelector("article.card");
  expect(article).toBeInTheDocument();
  expect(article).toHaveAttribute("aria-label", baseTicket.title);
  // urgent class when group is 0
  expect(article).toHaveClass("urgent");
});

test("renders meta information correctly", () => {
  const ticket = {
    ...baseTicket,
    priority: "urgent",
    due: "2023-12-31",
    status: "in_progress",
    assigned_to: "her",
  };
  const { getByText, container } = render(<TicketCard ticket={ticket} />);

  // title
  const titleEl = container.querySelector("h3.card-title");
  expect(titleEl).toBeInTheDocument();
  expect(titleEl).toHaveTextContent(ticket.title);

  // meta container
  const meta = container.querySelector("div.card-meta");
  expect(meta).toBeInTheDocument();

  // priority badge
  const badge = getByText(ticket.priority);
  expect(badge).toBeInTheDocument();
  expect(badge).toHaveClass(`priority-${ticket.priority}`);

  // due span only when set
  const due = container.querySelector("span.due");
  expect(due).toBeInTheDocument();
  expect(due).toHaveTextContent(`due ${ticket.due}`);

  // status pill with space in displayed text
  const pill = container.querySelector("span.pill");
  expect(pill).toBeInTheDocument();
  const displayedStatus = ticket.status.replace("_", " ");
  expect(pill).toHaveTextContent(displayedStatus);
  expect(pill).toHaveClass(`status-${ticket.status}`);

  // who span
  const who = container.querySelector("span.who");
  expect(who).toBeInTheDocument();
  expect(who).toHaveTextContent(`for ${ticket.assigned_to}`);
});

test("renders children conditionally", () => {
  const childButton = <button>Action</button>;
  const { container, rerender } = render(<TicketCard ticket={baseTicket}>{childButton}</TicketCard>);
  const actions = container.querySelector("div.card-actions");
  expect(actions).toBeInTheDocument();
  expect(actions).toContainElement(container.querySelector("button")!);

  // No children (undefined)
  rerender(<TicketCard ticket={baseTicket} />);
  expect(container.querySelector("div.card-actions")).not.toBeInTheDocument();

  // Children null
  rerender(<TicketCard ticket={baseTicket}>{null}</TicketCard>);
  expect(container.querySelector("div.card-actions")).not.toBeInTheDocument();

  // Children false
  // @ts-ignore – React allows boolean children
  rerender(<TicketCard ticket={baseTicket}>{false}</TicketCard>);
  expect(container.querySelector("div.card-actions")).not.toBeInTheDocument();
});

test("renders text as plain text not HTML", () => {
  const dangerousTitle = "<b>Bold</b> Title";
  const ticket = { ...baseTicket, title: dangerousTitle };
  const { container } = render(<TicketCard ticket={ticket} />);
  const article = container.querySelector("article.card");
  expect(article).toBeInTheDocument();
  // The raw HTML should not be parsed into a <b> element
  expect(article?.querySelector("b")).not.toBeInTheDocument();
  // The text should appear exactly as the string with angle brackets
  expect(article).toHaveTextContent(dangerousTitle);
});
