// GD-2j: frontend/src/Directions.tsx
import "@testing-library/jest-dom/vitest";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import Directions from "../src/Directions";

afterEach(cleanup);

const STEPS = [
  "Paste your token into the Token field and press Load.",
  "To ask your partner for something, fill in New ticket and press File ticket: it lands in their To Do column.",
  "Work the tickets filed for you: Acknowledge, then Start, then Done.",
  "When your partner marks your ticket Done, Close it, or Reopen it if it is not finished.",
  "The Household board shows every ticket for both of you, and hovering a title shows its details.",
];

describe("Directions", () => {
  it("is a section named Directions with the classes panel and directions and an h2 heading", () => {
    render(<Directions onClose={vi.fn()} />);
    const r = screen.getByRole("region", { name: "Directions" });
    expect(r.tagName).toBe("SECTION");
    expect(r).toHaveClass("panel", "directions");
    expect(within(r).getByRole("heading", { level: 2, name: "Directions" })).toBeInTheDocument();
  });

  it("holds an ordered list of exactly the five steps, in order", () => {
    render(<Directions onClose={vi.fn()} />);
    const list = screen.getByRole("list");
    expect(list.tagName).toBe("OL");
    expect(within(list).getAllByRole("listitem").map((li) => li.textContent)).toEqual(STEPS);
  });

  it("has a Close button that calls onClose once", () => {
    const onClose = vi.fn();
    render(<Directions onClose={onClose} />);
    fireEvent.click(screen.getByRole("button", { name: "Close" }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
