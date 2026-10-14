import "@testing-library/jest-dom/vitest";
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import Directions from "../src/Directions";

describe("Directions", () => {
  const onClose = vi.fn();

  it("renders the section with correct class and aria-label", () => {
    render(<Directions onClose={onClose} />);
    const section = screen.getByRole("region", { name: "Directions" });
    expect(section).toHaveClass("panel", "directions");
  });

  it("renders the h2 Directions heading", () => {
    render(<Directions onClose={onClose} />);
    const heading = screen.getByRole("heading", { name: "Directions" });
    expect(heading).toBeInTheDocument();
  });

  it("renders an ordered list with exactly five items in the correct order", () => {
    render(<Directions onClose={onClose} />);
    const list = screen.getByRole("list");
    expect(list).toBeInTheDocument();
    const items = screen.getAllByRole("listitem");
    expect(items).toHaveLength(5);
    expect(items[0]).toHaveTextContent("Paste your token into the Token field and press Load.");
    expect(items[1]).toHaveTextContent("To ask your partner for something, fill in New ticket and press File ticket: it lands in their To Do column.");
    expect(items[2]).toHaveTextContent("Work the tickets filed for you: Acknowledge, then Start, then Done.");
    expect(items[3]).toHaveTextContent("When your partner marks your ticket Done, Close it, or Reopen it if it is not finished.");
    expect(items[4]).toHaveTextContent("The Household board shows every ticket for both of you, and hovering a title shows its details.");
  });

  it("renders a Close button", () => {
    render(<Directions onClose={onClose} />);
    const button = screen.getByRole("button", { name: "Close" });
    expect(button).toBeInTheDocument();
  });

  it("calls onClose once when the Close button is clicked", () => {
    render(<Directions onClose={onClose} />);
    const button = screen.getByRole("button", { name: "Close" });
    button.click();
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
