// Vitest unit tests for fetchBoard and HouseholdBoard component
import "@testing-library/jest-dom/vitest";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import * as api from "../src/api";
import HouseholdBoard from "../src/HouseholdBoard";
import type { Board, Ticket } from "../src/types";

global.fetch = vi.fn();

afterEach(() => {
  cleanup();
});

describe("fetchBoard", () => {
  const token = "TOKEN";
  const mockBoard: Board = {
    todo: [],
    in_progress: [],
    completed: [],
  };

  beforeEach(() => {
    (global.fetch as ReturnType<typeof vi.fn>).mockReset();
  });

  test("testFetchBoardSuccess", async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
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

  test("testFetchBoardError", async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: false,
      status: 401,
    });
    await expect(api.fetchBoard(token)).rejects.toThrow("401");
  });

  // Clause 1: ensure fetchBoard is a named export and throws on non‑ok response
  test("testFetchBoardExportsAndErrorHandling", async () => {
    expect(typeof api.fetchBoard).toBe("function");
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: false,
      status: 500,
    });
    await expect(api.fetchBoard(token)).rejects.toThrow("500");
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

  test("testHouseholdBoardRendersPanelAndColumnsStructure", () => {
    render(<HouseholdBoard board={board} />);
    const panel = screen.getByLabelText("Household board");
    expect(panel).toBeInTheDocument();
    expect(panel).toHaveClass("panel");
    const heading = screen.getByRole("heading", { level: 2, name: "Household board" });
    expect(heading).toBeInTheDocument();
    const boardDiv = panel.querySelector("div.board");
    expect(boardDiv).toBeInTheDocument();
    const columnSections = boardDiv?.querySelectorAll("section.column");
    expect(columnSections?.length).toBe(3);
    const ariaLabels = Array.from(columnSections ?? []).map((c) => c.getAttribute("aria-label"));
    expect(ariaLabels).toEqual(["To Do", "In Progress", "Completed"]);
  });

  // Clause 3: each column title includes count and shows tickets or empty message
  test("testHouseholdBoardColumnTitlesCountsAndTicketOrEmptyMessage", () => {
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
