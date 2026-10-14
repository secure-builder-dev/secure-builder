import "@testing-library/jest-dom/vitest";
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import type { Board, Ticket } from "../src/types";
import * as api from "../src/api";
import HouseholdBoard from "../src/HouseholdBoard";
import TicketCard from "../src/TicketCard";

describe("fetchBoard", () => {
  const mockBoard: Board = {
    todo: [],
    in_progress: [],
    completed: [],
  };

  afterEach(() => {
    document.body.innerHTML = "";
    vi.restoreAllMocks();
  });

  it("exports fetchBoard from api.ts", () => {
    expect(api.fetchBoard).toBeDefined();
    expect(typeof api.fetchBoard).toBe("function");
  });

  it("fetchBoard sends GET /api/board with Authorization header", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockBoard,
    }) as any;

    await api.fetchBoard("test-token");

    expect(global.fetch).toHaveBeenCalledWith("/api/board", {
      method: "GET",
      headers: { Authorization: "Bearer test-token" },
    });
  });

  it("fetchBoard returns the parsed Board on success", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockBoard,
    }) as any;

    const result = await api.fetchBoard("test-token");

    expect(result).toEqual(mockBoard);
  });

  it("fetchBoard throws Error(String(status)) when response is not ok", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
    }) as any;

    await expect(api.fetchBoard("bad-token")).rejects.toThrow("401");
  });

  it("fetchBoard throws Error(String(status)) for 404", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
    }) as any;

    await expect(api.fetchBoard("bad-token")).rejects.toThrow("404");
  });

  it("fetchBoard throws Error(String(status)) for 500", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
    }) as any;

    await expect(api.fetchBoard("bad-token")).rejects.toThrow("500");
  });
});

describe("HouseholdBoard component", () => {
  const mockTicket: Ticket = {
    id: 1,
    title: "Test ticket",
    details: "Test details",
    priority: "normal",
    due: "2026-01-01",
    status: "open",
    filed_by: "her",
    assigned_to: "him",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };

  const emptyBoard: Board = {
    todo: [],
    in_progress: [],
    completed: [],
  };

  afterEach(() => {
    document.body.innerHTML = "";
    vi.restoreAllMocks();
  });

  it("default-exports HouseholdBoard component", () => {
    expect(HouseholdBoard).toBeDefined();
  });

  it("renders section with className panel and aria-label Household board", () => {
    render(<HouseholdBoard board={emptyBoard} />);
    const section = screen.getByLabelText("Household board");
    expect(section).toHaveClass("panel");
  });

  it("renders h2 with text Household board", () => {
    render(<HouseholdBoard board={emptyBoard} />);
    expect(screen.getByRole("heading", { name: "Household board" })).toBeInTheDocument();
  });

  it("renders div with className board", () => {
    render(<HouseholdBoard board={emptyBoard} />);
    const boardDiv = screen.getByLabelText("Household board").querySelector(".board");
    expect(boardDiv).toBeInTheDocument();
  });

  it("renders three column sections with correct aria-labels", () => {
    render(<HouseholdBoard board={emptyBoard} />);
    expect(screen.getByLabelText("To Do")).toBeInTheDocument();
    expect(screen.getByLabelText("In Progress")).toBeInTheDocument();
    expect(screen.getByLabelText("Completed")).toBeInTheDocument();
  });

  it("each column is a section with className column", () => {
    render(<HouseholdBoard board={emptyBoard} />);
    const columns = screen.getAllByRole("region", { hidden: true }).filter(
      (el) => el.classList.contains("column")
    );
    expect(columns).toHaveLength(3);
  });

  it("each column has h3.column-title with name and span.count", () => {
    render(<HouseholdBoard board={emptyBoard} />);
    const todoTitle = screen.getByText(/To Do/).closest("h3");
    expect(todoTitle).toHaveClass("column-title");
    expect(todoTitle?.querySelector(".count")).toBeInTheDocument();

    const inProgressTitle = screen.getByText(/In Progress/).closest("h3");
    expect(inProgressTitle).toHaveClass("column-title");
    expect(inProgressTitle?.querySelector(".count")).toBeInTheDocument();

    const completedTitle = screen.getByText(/Completed/).closest("h3");
    expect(completedTitle).toHaveClass("column-title");
    expect(completedTitle?.querySelector(".count")).toBeInTheDocument();
  });

  it("shows TicketCard per ticket in each column", () => {
    const boardWithTickets: Board = {
      todo: [mockTicket],
      in_progress: [mockTicket],
      completed: [mockTicket],
    };
    render(<HouseholdBoard board={boardWithTickets} />);
    expect(screen.getAllByText("Test ticket")).toHaveLength(3);
  });

  it("shows p.empty with Nothing here when column has no tickets", () => {
    render(<HouseholdBoard board={emptyBoard} />);
    const emptyParagraphs = screen.getAllByText(/Nothing here/);
    expect(emptyParagraphs).toHaveLength(3);
    emptyParagraphs.forEach((p) => expect(p).toHaveClass("empty"));
  });

  it("TicketCard has no children when rendered in HouseholdBoard", () => {
    const boardWithTickets: Board = {
      todo: [mockTicket],
      in_progress: [],
      completed: [],
    };
    render(<HouseholdBoard board={boardWithTickets} />);
    const ticketCard = screen.getByLabelText("Test ticket");
    expect(ticketCard.querySelector(".card-actions")).not.toBeInTheDocument();
  });
});

export {};

