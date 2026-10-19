
import "@testing-library/jest-dom/vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import TicketCard from "../src/TicketCard";
import { test, expect, afterEach } from "vitest";
import type { Ticket } from "../src/types";
+
+afterEach(() => {
+  cleanup();
+});
@@
-  const title = screen.getByRole("heading", { level: 3, name: sampleTicket.title });
-  const hoverSpan = title.closest("span.hover-target");
+  const title = screen.getByRole("heading", { level: 3, name: sampleTicket.title });
+  const hoverSpan = title.closest("span.hover-target");
@@
-  const hoverSpan = screen.getByText(sampleTicket.title).closest("span.hover-target");
+  const hoverSpan = screen.getAllByText(sampleTicket.title)[0].closest("span.hover-target");
@@
-  const hoverSpan = screen.getByText(sampleTicket.title).closest("span.hover-target");
+  const hoverSpan = screen.getAllByText(sampleTicket.title)[0].closest("span.hover-target");
@@
-  const article = screen.getByRole("article", { name: sampleTicket.title });
+  const article = screen.getAllByRole("article", { name: sampleTicket.title })[0];
*** End Patch


const sampleTicket: Ticket = {
  id: 1,
  title: "Sample Ticket",
  details: "Some details",
  priority: "normal",
  due: null,
  status: "open",
  filed_by: "her",
  assigned_to: "him",
  created_at: "2023-01-01T00:00:00Z",
  updated_at: "2023-01-01T00:00:00Z",
};

test("title is wrapped in HoverCard span.hover-target", () => {
  render(<TicketCard ticket={sampleTicket} />);
  const title = screen.getByRole("heading", { level: 3, name: sampleTicket.title });
  const hoverSpan = title.closest("span.hover-target");
  expect(hoverSpan).toBeInTheDocument();
});

test("hovering over title shows tooltip with ticket details", async () => {
  render(<TicketCard ticket={sampleTicket} />);
  const hoverSpan = screen.getByText(sampleTicket.title).closest("span.hover-target");
  expect(hoverSpan).toBeInTheDocument();
  fireEvent.mouseEnter(hoverSpan!);
  const tooltip = await screen.findByRole("tooltip");
  expect(tooltip).toBeInTheDocument();
  expect(tooltip).toHaveTextContent(sampleTicket.details);
});

test("focusing title shows tooltip", async () => {
  render(<TicketCard ticket={sampleTicket} />);
  const hoverSpan = screen.getByText(sampleTicket.title).closest("span.hover-target");
  expect(hoverSpan).toBeInTheDocument();
  fireEvent.focus(hoverSpan!);
  const tooltip = await screen.findByRole("tooltip");
  expect(tooltip).toBeInTheDocument();
});

test("other TicketCard structure remains unchanged", () => {
  render(
    <TicketCard ticket={sampleTicket}>
      <button>Action</button>
    </TicketCard>,
  );
  const article = screen.getByRole("article", { name: sampleTicket.title });
  expect(article).toHaveClass("card");
  const meta = screen.getByText(`for ${sampleTicket.assigned_to}`);
  expect(meta).toBeInTheDocument();
  const actions = screen.getByText("Action");
  expect(actions).toBeInTheDocument();
});
