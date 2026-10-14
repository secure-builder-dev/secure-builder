import "@testing-library/jest-dom/vitest";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup, fireEvent } from "@testing-library/react";
import Directions from "../src/Directions";

describe("Directions", () => {
  let onClose: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    onClose = vi.fn();
  });

  it("renders the section with correct class and aria-label", () => {
    render(<Directions onClose={onClose} />);
    const section = screen.getByRole("region", { name: "Directions" });
    expect(section).toHaveClass("panel", "directions");
  });

  it("renders the h2 Directions heading", () => {
    render(<Directions onClose={onClose} />);
    const section = screen.getByRole("region", { name: "Directions" });
    const heading = section.querySelector("h2");
    expect(heading).toBeInTheDocument();
    expect(heading?.textContent).toBe("Directions");
  });

  it("renders an ordered list with exactly five items in the correct order", () => {
    render(<Directions onClose={onClose} />);
    const section = screen.getByRole("region", { name: "Directions" });
    const list = section.querySelector("ol");
    expect(list).toBeInTheDocument();
    const items = list?.querySelectorAll("li");
    expect(items).toHaveLength(5);
    expect(items?.[0]?.textContent).toBe("Paste your token into the Token field and press Load.");
    expect(items?.[1]?.textContent).toBe("To ask your partner for something, fill in New ticket and press File ticket: it lands in their To Do column.");
    expect(items?.[2]?.textContent).toBe("Work the tickets filed for you: Acknowledge, then Start, then Done.");
    expect(items?.[3]?.textContent).toBe("When your partner marks your ticket Done, Close it, or Reopen it if it is not finished.");
    expect(items?.[4]?.textContent).toBe("The Household board shows every ticket for both of you, and hovering a title shows its details.");
  });

  it("renders a Close button", () => {
    render(<Directions onClose={onClose} />);
    const section = screen.getByRole("region", { name: "Directions" });
    const button = section.querySelector("button");
    expect(button).toBeInTheDocument();
    expect(button?.textContent).toBe("Close");
  });

  it("calls onClose once when the Close button is clicked", () => {
    render(<Directions onClose={onClose} />);
    const section = screen.getByRole("region", { name: "Directions" });
    const button = section.querySelector("button");
    fireEvent.click(button!);
    expect(onClose).toHaveBeenCalledTimes(1);
  });



  afterEach(() => {
    cleanup();
  });
});
