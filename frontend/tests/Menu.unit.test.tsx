// GD-2i: frontend/src/Menu.tsx
import "@testing-library/jest-dom/vitest";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import Menu from "../src/Menu";

afterEach(cleanup);

describe("Menu", () => {
  it("renders a Menu button with the class menu-button showing ☰, closed at first", () => {
    render(<Menu onDirections={vi.fn()} />);
    const b = screen.getByRole("button", { name: "Menu" });
    expect(b).toHaveClass("menu-button");
    expect(b.textContent).toBe("☰");
    expect(b).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("navigation", { name: "Main menu" })).toBeNull();
  });

  it("clicking Menu opens the Main menu navigation (class menu) holding a Directions button", () => {
    render(<Menu onDirections={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Menu" }));
    const nav = screen.getByRole("navigation", { name: "Main menu" });
    expect(nav).toHaveClass("menu");
    expect(within(nav).getByRole("button", { name: "Directions" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Menu" })).toHaveAttribute("aria-expanded", "true");
  });

  it("clicking Menu again closes it", () => {
    render(<Menu onDirections={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Menu" }));
    fireEvent.click(screen.getByRole("button", { name: "Menu" }));
    expect(screen.queryByRole("navigation", { name: "Main menu" })).toBeNull();
    expect(screen.getByRole("button", { name: "Menu" })).toHaveAttribute("aria-expanded", "false");
  });

  it("clicking Directions calls onDirections once and closes the menu", () => {
    const onDirections = vi.fn();
    render(<Menu onDirections={onDirections} />);
    fireEvent.click(screen.getByRole("button", { name: "Menu" }));
    fireEvent.click(screen.getByRole("button", { name: "Directions" }));
    expect(onDirections).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("navigation", { name: "Main menu" })).toBeNull();
    expect(screen.getByRole("button", { name: "Menu" })).toHaveAttribute("aria-expanded", "false");
  });
});
