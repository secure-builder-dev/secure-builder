// GD-2k: frontend/src/App.tsx shows the Menu in the top bar and the Directions when chosen.
import "@testing-library/jest-dom/vitest";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import App from "../src/App";
import { mockApi, region, signIn } from "./helpers";

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

function openDirections() {
  fireEvent.click(within(screen.getByRole("banner")).getByRole("button", { name: "Menu" }));
  fireEvent.click(screen.getByRole("button", { name: "Directions" }));
}

describe("App: menu and directions", () => {
  it("shows the Menu button inside the top bar, before and after Load", async () => {
    mockApi();
    render(<App />);
    expect(within(screen.getByRole("banner")).getByRole("button", { name: "Menu" })).toBeInTheDocument();
    await signIn();
    expect(within(screen.getByRole("banner")).getByRole("button", { name: "Menu" })).toBeInTheDocument();
  });

  it("shows no Directions section until Directions is chosen", () => {
    mockApi();
    render(<App />);
    expect(screen.queryByRole("region", { name: "Directions" })).toBeNull();
    openDirections();
    const d = region("Directions");
    expect(screen.getByRole("main").contains(d)).toBe(true);
    expect(within(d).getAllByRole("listitem")).toHaveLength(5);
  });

  it("the Directions Close button hides it again", () => {
    mockApi();
    render(<App />);
    openDirections();
    fireEvent.click(within(region("Directions")).getByRole("button", { name: "Close" }));
    expect(screen.queryByRole("region", { name: "Directions" })).toBeNull();
  });

  it("choosing Directions fetches nothing and leaves the loaded page as it was", async () => {
    const api = mockApi();
    render(<App />);
    await signIn();
    const before = api.fn.mock.calls.length;
    openDirections();
    expect(api.fn.mock.calls.length).toBe(before);
    expect(region("My board")).toBeInTheDocument();
    expect(region("Directions")).toBeInTheDocument();
  });
});
