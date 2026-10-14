import "@testing-library/jest-dom/vitest";
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import Menu from "../src/Menu";

describe("Menu", () => {
  let onDirections: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    onDirections = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the menu button closed at first", () => {
    render(<Menu onDirections={onDirections} />);
    const button = screen.getByRole("button", { name: /menu/i });
    expect(button).toHaveClass("menu-button");
    expect(button).toHaveAttribute("aria-label", "Menu");
    expect(button).toHaveAttribute("aria-expanded", "false");
    expect(button).toHaveTextContent("☰");
  });

  it("opens the menu when the button is clicked", () => {
    render(<Menu onDirections={onDirections} />);
    const button = screen.getByRole("button", { name: /menu/i });
    fireEvent.click(button);
    expect(button).toHaveAttribute("aria-expanded", "true");
    const nav = screen.getByRole("navigation", { name: /main menu/i });
    expect(nav).toBeInTheDocument();
    expect(nav).toHaveClass("menu");
  });

  it("holds a Directions button when open", () => {
    render(<Menu onDirections={onDirections} />);
    const menuButton = screen.getByRole("button", { name: /menu/i });
    fireEvent.click(menuButton);
    const directionsButton = screen.getByRole("button", { name: /directions/i });
    expect(directionsButton).toBeInTheDocument();
  });

  it("closes the menu and calls onDirections once when Directions is clicked", () => {
    render(<Menu onDirections={onDirections} />);
    const menuButton = screen.getByRole("button", { name: /menu/i });
    fireEvent.click(menuButton);
    expect(menuButton).toHaveAttribute("aria-expanded", "true");
    const directionsButton = screen.getByRole("button", { name: /directions/i });
    fireEvent.click(directionsButton);
    expect(menuButton).toHaveAttribute("aria-expanded", "false");
    expect(onDirections).toHaveBeenCalledTimes(1);
  });

  it("toggles the menu closed when the button is clicked again", () => {
    render(<Menu onDirections={onDirections} />);
    const button = screen.getByRole("button", { name: /menu/i });
    fireEvent.click(button);
    expect(button).toHaveAttribute("aria-expanded", "true");
    fireEvent.click(button);
    expect(button).toHaveAttribute("aria-expanded", "false");
  });
});
