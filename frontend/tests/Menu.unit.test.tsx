import "@testing-library/jest-dom/vitest";
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import Menu from "../src/Menu";

describe("Menu", () => {
  let onDirections: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    onDirections = vi.fn();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("renders the menu button closed at first", () => {
    render(<Menu onDirections={onDirections} />);
    const button = screen.getByRole("button", { name: "Menu" });
    expect(button).toHaveClass("menu-button");
    expect(button).toHaveAttribute("aria-label", "Menu");
    expect(button).toHaveAttribute("aria-expanded", "false");
    expect(button).toHaveTextContent("☰");
  });

  it("opens the menu when the button is clicked", () => {
    render(<Menu onDirections={onDirections} />);
    const button = screen.getByRole("button", { name: "Menu" });
    fireEvent.click(button);
    expect(button).toHaveAttribute("aria-expanded", "true");
    const nav = screen.getByRole("navigation", { name: "Main menu" });
    expect(nav).toBeInTheDocument();
    expect(nav).toHaveClass("menu");
  });

  it("holds a Directions button when open", () => {
    render(<Menu onDirections={onDirections} />);
    const menuButton = screen.getByRole("button", { name: "Menu" });
    fireEvent.click(menuButton);
    const directionsButton = screen.getByRole("button", { name: "Directions" });
    expect(directionsButton).toBeInTheDocument();
  });

  it("closes the menu and calls onDirections once when Directions is clicked", () => {
    render(<Menu onDirections={onDirections} />);
    const menuButton = screen.getByRole("button", { name: "Menu" });
    fireEvent.click(menuButton);
    expect(menuButton).toHaveAttribute("aria-expanded", "true");
    const directionsButton = screen.getByRole("button", { name: "Directions" });
    fireEvent.click(directionsButton);
    expect(menuButton).toHaveAttribute("aria-expanded", "false");
    expect(onDirections).toHaveBeenCalledTimes(1);
  });

  it("toggles the menu closed when the button is clicked again", () => {
    render(<Menu onDirections={onDirections} />);
    const button = screen.getByRole("button", { name: "Menu" });
    fireEvent.click(button);
    expect(button).toHaveAttribute("aria-expanded", "true");
    fireEvent.click(button);
    expect(button).toHaveAttribute("aria-expanded", "false");
  });

  it("does not show the menu navigation when closed", () => {
    render(<Menu onDirections={onDirections} />);
    expect(screen.queryByRole("navigation", { name: "Main menu" })).not.toBeInTheDocument();
  });

  it("does not call onDirections when the Menu button is clicked", () => {
    render(<Menu onDirections={onDirections} />);
    const button = screen.getByRole("button", { name: "Menu" });
    fireEvent.click(button);
    expect(onDirections).not.toHaveBeenCalled();
  });

  it("does not call onDirections when clicking the menu button while open", () => {
    render(<Menu onDirections={onDirections} />);
    const button = screen.getByRole("button", { name: "Menu" });
    fireEvent.click(button);
    fireEvent.click(button);
    expect(onDirections).not.toHaveBeenCalled();
  });
});
