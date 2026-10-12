// GD-2e: frontend/src/HouseholdBoard.tsx and fetchBoard in frontend/src/api.ts
import "@testing-library/jest-dom/vitest";
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import HouseholdBoard from "../src/HouseholdBoard";
import { fetchBoard } from "../src/api";
import { board, card, cards, column, mockApi, region, ticket } from "./helpers";

afterEach(cleanup);

const B = board({
  todo: [ticket({ title: "For him", assigned_to: "him" }), ticket({ title: "For her", assigned_to: "her" })],
  in_progress: [ticket({ title: "Doing", status: "in_progress", assigned_to: "him" })],
  completed: [],
});

describe("fetchBoard", () => {
  it("sends GET /api/board with the bearer token and returns the board", async () => {
    const api = mockApi({ "GET /api/board": { body: B } });
    await expect(fetchBoard("tok-b")).resolves.toEqual(B);
    expect(api.calls("GET /api/board")[0].headers["authorization"]).toBe("Bearer tok-b");
  });

  it("throws Error(status) on a non-ok answer", async () => {
    mockApi({ "GET /api/board": { status: 500, body: {} } });
    await expect(fetchBoard("t")).rejects.toThrow(new Error("500"));
  });
});

describe("HouseholdBoard", () => {
  it("is a panel section named Household board with an h2 heading", () => {
    render(<HouseholdBoard board={B} />);
    const r = region("Household board");
    expect(r.tagName).toBe("SECTION");
    expect(r).toHaveClass("panel");
    expect(within(r).getByRole("heading", { level: 2, name: "Household board" })).toBeInTheDocument();
  });

  it("has the three columns inside one .board, each a .column with a .column-title and .count", () => {
    render(<HouseholdBoard board={B} />);
    const grid = region("Household board").querySelector(".board")!;
    expect(grid).not.toBeNull();
    for (const [name, n] of [["To Do", "2"], ["In Progress", "1"], ["Completed", "0"]]) {
      const col = column("Household board", name);
      expect(col).toHaveClass("column");
      expect(grid.contains(col)).toBe(true);
      expect(col.querySelector(".column-title")!.textContent).toContain(name);
      expect(col.querySelector(".count")!.textContent).toBe(n);
    }
  });

  it("puts every ticket on its own TicketCard in its column", () => {
    render(<HouseholdBoard board={B} />);
    expect(cards(column("Household board", "To Do")).map((c) => c.getAttribute("aria-label"))).toEqual(["For him", "For her"]);
    expect(card("Doing", column("Household board", "In Progress"))).toHaveClass("card");
  });

  it("each card says who it is for", () => {
    render(<HouseholdBoard board={B} />);
    expect(within(card("For him")).getByText("for him")).toBeInTheDocument();
    expect(within(card("For her")).getByText("for her")).toBeInTheDocument();
  });

  it("an empty column shows Nothing here", () => {
    render(<HouseholdBoard board={B} />);
    expect(within(column("Household board", "Completed")).getByText("Nothing here")).toHaveClass("empty");
  });

  it("cards on the household board have no action buttons", () => {
    render(<HouseholdBoard board={B} />);
    expect(screen.queryAllByRole("button")).toHaveLength(0);
  });
});
