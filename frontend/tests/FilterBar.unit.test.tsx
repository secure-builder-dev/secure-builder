import "@testing-library/jest-dom/vitest";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import FilterBar from "../src/FilterBar";
import SummaryBadge from "../src/SummaryBadge";

describe("FilterBar", () => {
  let onApply: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    onApply = vi.fn();
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  it("renders form.filter-bar with role search named Filter household board", () => {
    render(<FilterBar onApply={onApply} />);
    const form = screen.getByRole("search", { name: /filter household board/i });
    expect(form).toHaveClass("filter-bar");
  });

  it("holds the labelled field Search (text)", () => {
    render(<FilterBar onApply={onApply} />);
    const input = screen.getByLabelText(/search/i);
    expect(input).toBeInTheDocument();
    expect(input.tagName).toBe("INPUT");
    expect((input as HTMLInputElement).type).toBe("text");
  });

  it("holds the labelled field Priority (a select of Any with the empty value, low, normal, urgent)", () => {
    render(<FilterBar onApply={onApply} />);
    const select = screen.getByLabelText(/priority/i);
    expect(select).toBeInTheDocument();
    expect(select.tagName).toBe("SELECT");

    const options = Array.from((select as HTMLSelectElement).options);
    expect(options).toHaveLength(4);
    expect(options[0].value).toBe("");
    expect(options[0].textContent.trim()).toBe("Any");
    expect(options[1].value).toBe("low");
    expect(options[2].value).toBe("normal");
    expect(options[3].value).toBe("urgent");
  });

  it("holds the labelled field Assigned to (a select of Anyone with the empty value, her, him)", () => {
    render(<FilterBar onApply={onApply} />);
    const select = screen.getByLabelText(/assigned to/i);
    expect(select).toBeInTheDocument();
    expect(select.tagName).toBe("SELECT");

    const options = Array.from((select as HTMLSelectElement).options);
    expect(options).toHaveLength(3);
    expect(options[0].value).toBe("");
    expect(options[0].textContent.trim()).toBe("Anyone");
    expect(options[1].value).toBe("her");
    expect(options[2].value).toBe("him");
  });

  it("holds an Apply submit button", () => {
    render(<FilterBar onApply={onApply} />);
    const button = screen.getByRole("button", { name: /apply/i });
    expect(button).toBeInTheDocument();
    expect((button as HTMLButtonElement).type).toBe("submit");
  });

  it("calls onApply with stripped q and empty strings for no filter when Apply is clicked", () => {
    render(<FilterBar onApply={onApply} />);

    fireEvent.change(screen.getByLabelText(/search/i), { target: { value: "  hello world  " } });
    fireEvent.change(screen.getByLabelText(/priority/i), { target: { value: "urgent" } });
    fireEvent.change(screen.getByLabelText(/assigned to/i), { target: { value: "her" } });

    fireEvent.click(screen.getByRole("button", { name: /apply/i }));

    expect(onApply).toHaveBeenCalledWith({
      q: "hello world",
      priority: "urgent",
      assigned_to: "her",
    });
  });

  it("calls onApply with empty strings when fields are left at defaults and Apply is clicked", () => {
    render(<FilterBar onApply={onApply} />);

    fireEvent.click(screen.getByRole("button", { name: /apply/i }));

    expect(onApply).toHaveBeenCalledWith({
      q: "",
      priority: "",
      assigned_to: "",
    });
  });
});

describe("SummaryBadge", () => {
  it("renders span.summary named Summary with the correct text for given numbers", () => {
    const summary = { overdue: 2, due_today: 1, open: 5 };
    render(<SummaryBadge summary={summary} />);

    const badge = screen.getByRole("status", { name: /summary/i });
    expect(badge).toBeInTheDocument();
    expect(badge.tagName).toBe("SPAN");
    expect(badge).toHaveClass("summary");
    expect(badge).toHaveTextContent("2 overdue \u00b7 1 due today \u00b7 5 open");
  });

  it("has the class alert when overdue is more than 0", () => {
    const summary = { overdue: 3, due_today: 0, open: 10 };
    render(<SummaryBadge summary={summary} />);

    const badge = screen.getByRole("status", { name: /summary/i });
    expect(badge).toHaveClass("alert");
  });

  it("does not have the class alert when overdue is 0", () => {
    const summary = { overdue: 0, due_today: 5, open: 20 };
    render(<SummaryBadge summary={summary} />);

    const badge = screen.getByRole("status", { name: /summary/i });
    expect(badge).not.toHaveClass("alert");
  });
});
