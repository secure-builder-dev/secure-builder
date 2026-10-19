// Vitest unit tests for fetchBoard and HouseholdBoard component
import "@testing-library/jest-dom/vitest";
import { beforeEach, describe, expect, test } from "vitest";
import { render, screen } from "@testing-library/react";
import * as api from "../src/api";
import HouseholdBoard from "../src/HouseholdBoard";
import TicketCard from "../src/TicketCard";
import type { Board, Ticket } from "../src/types";

global.fetch = jest.fn();

describe("fetchBoard", () => {
  const token = "TOKEN";
  const mockBoard: Board = {
    todo: [],
    in_progress: [],
    completed: [],
  };

  beforeEach(() => {
    (global.fetch as jest.Mock).mockReset();
  });

  test("calls GET /api/board and returns parsed JSON on success", async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockBoard,
    });
    const result = await api.fetchBoard(token);
    expect(global.fetch).toHaveBeenCalledWith("/api/board", {
      method: "GET",
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(result).toEqual(mockBoard);
  });

  test("throws Error with status code when response not ok", async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: false,
      status: 401,
    });
    await expect(api.fetchBoard(token)).rejects.toThrow("401");
  });
});

describe("HouseholdBoard component", () => {
  const makeTicket = (id: number, title: string): Ticket => ({
    id,
    title,
    details: "",
    priority: "normal",
    due: null,
    status: "open",
    filed_by: "her",
    assigned_to: "him",
    created_at: "",
    updated_at: "",
  });

  const board: Board = {
    todo: [makeTicket(1, "Todo 1")],
    in_progress: [],
    completed: [makeTicket(2, "Done 1"), makeTicket(3, "Done 2")],
  };

  test("renders panel with correct aria-label, heading and three columns", () => {
    render(<HouseholdBoard board={board} />);
    const panel = screen.getByLabelText("Household board");
    expect(panel).toBeInTheDocument();
    expect(panel).toHaveClass("panel");
    const heading = screen.getByRole("heading", { level: 2, name: "Household board" });
    expect(heading).toBeInTheDocument();
    const columns = screen.getAllByRole("region", { name: /To Do|In Progress|Completed/ });
    expect(columns).toHaveLength(3);
  });

  test("each column shows title with count and renders tickets or empty message", () => {
    render(<HouseholdBoard board={board} />);
    // To Do column
    const todoTitle = screen.getByText(/To Do/);
    expect(todoTitle).toBeInTheDocument();
    const todoCount = screen.getByText("1");
    expect(todoCount).toBeInTheDocument();
    const todoCard = screen.getByLabelText("Todo 1");
    expect(todoCard).toBeInTheDocument();

    // In Progress column (empty)
    const inProgTitle = screen.getByText(/In Progress/);
    expect(inProgTitle).toBeInTheDocument();
    const emptyMsgs = screen.getAllByText("Nothing here");
    expect(emptyMsgs.length).toBeGreaterThanOrEqual(1);

    // Completed column
    const completedTitle = screen.getByText(/Completed/);
    expect(completedTitle).toBeInTheDocument();
    const completedCount = screen.getByText("2");
    expect(completedCount).toBeInTheDocument();
    const done1 = screen.getByLabelText("Done 1");
    const done2 = screen.getByLabelText("Done 2");
    expect(done1).toBeInTheDocument();
    expect(done2).toBeInTheDocument();
  });
});
