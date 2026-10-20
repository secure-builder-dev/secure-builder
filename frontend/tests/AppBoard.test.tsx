// GD-2f: frontend/src/App.tsx shows the HouseholdBoard.
import "@testing-library/jest-dom/vitest";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import App from "../src/App";
import { board, card, column, mockApi, region, settle, signIn, ticket } from "./helpers";

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

const HB = board({
  todo: [ticket({ title: "House A", assigned_to: "him" })],
  in_progress: [ticket({ title: "House B", status: "in_progress", assigned_to: "her" })],
});

describe("App: Household board", () => {
  it("Load fetches /api/board with the token and shows the Household board", async () => {
    const api = mockApi({ "GET /api/board": { body: HB } });
    render(<App />);
    await signIn("tok-x");
    expect(api.calls("GET /api/board")).toHaveLength(1);
    expect(api.calls("GET /api/board")[0].headers["authorization"]).toBe("Bearer tok-x");
    expect(card("House A", column("Household board", "To Do"))).toBeInTheDocument();
    expect(within(card("House B", region("Household board"))).getByText("for her")).toBeInTheDocument();
  });

  it("shows the Household board inside main, after My board and Tickets I filed", async () => {
    mockApi({ "GET /api/board": { body: HB } });
    render(<App />);
    await signIn();
    const main = screen.getByRole("main");
    const names = within(main).getAllByRole("region").map((r) => r.getAttribute("aria-label"))
      .filter((n) => ["My board", "Tickets I filed", "Household board"].includes(n ?? ""));
    expect(names).toEqual(["My board", "Tickets I filed", "Household board"]);
  });

  it("reloads the Household board after a ticket is filed", async () => {
    const api = mockApi({ "GET /api/board": { body: HB } });
    render(<App />);
    await signIn();
    api.routes["GET /api/board"] = { body: board({ todo: [ticket({ title: "House C", assigned_to: "him" })] }) };
    fireEvent.change(within(region("New ticket")).getByLabelText("Title"), { target: { value: "House C" } });
    fireEvent.click(within(region("New ticket")).getByRole("button", { name: "File ticket" }));
    await settle();
    expect(api.calls("GET /api/board")).toHaveLength(2);
    expect(card("House C", region("Household board"))).toBeInTheDocument();
  });

  it("a failed /api/board shows no Household board and no error, and the rest of the page works", async () => {
    mockApi({ "GET /api/board": { status: 500, body: {} },
              "GET /api/dashboard": { body: board({ todo: [ticket({ title: "Mine" })] }) } });
    render(<App />);
    await signIn();
    expect(screen.queryByRole("region", { name: "Household board" })).toBeNull();
    expect(screen.queryByRole("alert")).toBeNull();
    expect(card("Mine", region("My board"))).toBeInTheDocument();
  });

  it("a malformed /api/board answer is treated like a failed one", async () => {
    mockApi({ "GET /api/board": { body: { nope: true } } });
    render(<App />);
    await signIn();
    expect(screen.queryByRole("region", { name: "Household board" })).toBeNull();
    expect(screen.queryByRole("alert")).toBeNull();
    expect(region("My board")).toBeInTheDocument();
  });
});
