import "@testing-library/jest-dom/vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import Directions from "../src/Directions";

test("test_renders_Directions_section_with_correct_structure", () => {
  const onClose = vi.fn();
  render(<Directions onClose={onClose} />);

  // Section with aria-label "Directions"
  const section = screen.getByLabelText("Directions");
  expect(section).toBeInTheDocument();
  expect(section).toHaveClass("panel", "directions");

  // Heading level 2
  const heading = screen.getByRole("heading", { level: 2, name: "Directions" });
  expect(heading).toBeInTheDocument();

  // Ordered list
  const list = screen.getByRole("list");
  expect(list).toBeInTheDocument();
  expect(list.tagName).toBe("OL");

  // Close button calls onClose once
  const button = screen.getByRole("button", { name: /close/i });
  fireEvent.click(button);
  expect(onClose).toHaveBeenCalledTimes(1);
});

test("test_renders_list_with_exact_five_items_in_order", () => {
  const onClose = vi.fn();
  render(<Directions onClose={onClose} />);

  const items = screen.getAllByRole("listitem");
  const expected = [
    "Paste your token into the Token field and press Load.",
    "To ask your partner for something, fill in New ticket and press File ticket: it lands in their To Do column.",
    "Work the tickets filed for you: Acknowledge, then Start, then Done.",
    "When your partner marks your ticket Done, Close it, or Reopen it if it is not finished.",
    "The Household board shows every ticket for both of you, and hovering a title shows its details."
  ];

  expect(items).toHaveLength(5);
  items.forEach((item, i) => {
    expect(item).toHaveTextContent(expected[i]);
  });
});
