// GD-2a: frontend/src/HoverCard.tsx
import "@testing-library/jest-dom/vitest";
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import HoverCard from "../src/HoverCard";
import { ticket } from "./helpers";

afterEach(cleanup);

const T = ticket({ details: "Under the sink, left pipe", filed_by: "her", assigned_to: "him",
                   created_at: "2026-10-03T08:15:00+00:00" });

function target() {
  return screen.getByText("Fix it").closest(".hover-target") as HTMLElement;
}

describe("HoverCard", () => {
  it("renders its children inside a span with the class hover-target that can take focus", () => {
    render(<HoverCard ticket={T}>Fix it</HoverCard>);
    const span = target();
    expect(span.tagName).toBe("SPAN");
    expect(span).toHaveAttribute("tabindex", "0");
    expect(screen.queryByRole("tooltip")).toBeNull();
  });

  it("shows a tooltip with the class hover-card while the pointer is over it", () => {
    render(<HoverCard ticket={T}>Fix it</HoverCard>);
    fireEvent.mouseEnter(target());
    expect(screen.getByRole("tooltip")).toHaveClass("hover-card");
    fireEvent.mouseLeave(target());
    expect(screen.queryByRole("tooltip")).toBeNull();
  });

  it("shows the tooltip while it has keyboard focus", () => {
    render(<HoverCard ticket={T}>Fix it</HoverCard>);
    fireEvent.focus(target());
    expect(screen.getByRole("tooltip")).toBeInTheDocument();
    fireEvent.blur(target());
    expect(screen.queryByRole("tooltip")).toBeNull();
  });

  it("the tooltip shows details, Filed by, Assigned to and Created (the date only)", () => {
    render(<HoverCard ticket={T}>Fix it</HoverCard>);
    fireEvent.mouseEnter(target());
    const tip = screen.getByRole("tooltip");
    expect(within(tip).getByText("Under the sink, left pipe")).toBeInTheDocument();
    expect(within(tip).getByText("Filed by her")).toBeInTheDocument();
    expect(within(tip).getByText("Assigned to him")).toBeInTheDocument();
    expect(within(tip).getByText("Created 2026-10-03")).toBeInTheDocument();
  });

  it("shows No details when details is empty", () => {
    render(<HoverCard ticket={{ ...T, details: "" }}>Fix it</HoverCard>);
    fireEvent.mouseEnter(target());
    expect(within(screen.getByRole("tooltip")).getByText("No details")).toBeInTheDocument();
  });

  it("renders details as text, never as HTML", () => {
    render(<HoverCard ticket={{ ...T, details: "<img src=x onerror=alert(1)>" }}>Fix it</HoverCard>);
    fireEvent.mouseEnter(target());
    expect(screen.getByText("<img src=x onerror=alert(1)>")).toBeInTheDocument();
    expect(document.querySelector("img")).toBeNull();
  });
});
