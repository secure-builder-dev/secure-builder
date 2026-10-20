// TO-4g: frontend/src/FilterBar.tsx and frontend/src/SummaryBadge.tsx
import "@testing-library/jest-dom/vitest";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import FilterBar from "../src/FilterBar";
import SummaryBadge from "../src/SummaryBadge";

afterEach(cleanup);

function bar() {
  return screen.getByRole("search", { name: "Filter household board" });
}

function options(select: HTMLElement) {
  return Array.from((select as HTMLSelectElement).options).map((o) => [o.textContent, o.value]);
}

describe("FilterBar", () => {
  it("is a form.filter-bar with role search named Filter household board", () => {
    render(<FilterBar onApply={() => {}} />);
    const f = bar();
    expect(f.tagName).toBe("FORM");
    expect(f).toHaveClass("filter-bar");
  });

  it("has a text field labelled Search, empty at first", () => {
    render(<FilterBar onApply={() => {}} />);
    const s = within(bar()).getByLabelText("Search") as HTMLInputElement;
    expect(s.tagName).toBe("INPUT");
    expect(s.type).toBe("text");
    expect(s.value).toBe("");
  });

  it("has a Priority select of Any (the empty value), low, normal, urgent, set to Any", () => {
    render(<FilterBar onApply={() => {}} />);
    const p = within(bar()).getByLabelText("Priority") as HTMLSelectElement;
    expect(p.tagName).toBe("SELECT");
    expect(options(p)).toEqual([["Any", ""], ["low", "low"], ["normal", "normal"], ["urgent", "urgent"]]);
    expect(p.value).toBe("");
  });

  it("has an Assigned to select of Anyone (the empty value), her, him, set to Anyone", () => {
    render(<FilterBar onApply={() => {}} />);
    const a = within(bar()).getByLabelText("Assigned to") as HTMLSelectElement;
    expect(a.tagName).toBe("SELECT");
    expect(options(a)).toEqual([["Anyone", ""], ["her", "her"], ["him", "him"]]);
    expect(a.value).toBe("");
  });

  it("has an Apply submit button", () => {
    render(<FilterBar onApply={() => {}} />);
    expect(within(bar()).getByRole("button", { name: "Apply" })).toHaveAttribute("type", "submit");
  });

  it("Apply with nothing chosen calls onApply with empty strings", () => {
    const onApply = vi.fn();
    render(<FilterBar onApply={onApply} />);
    fireEvent.click(within(bar()).getByRole("button", { name: "Apply" }));
    expect(onApply).toHaveBeenCalledTimes(1);
    expect(onApply).toHaveBeenCalledWith({ q: "", priority: "", assigned_to: "" });
  });

  it("Apply calls onApply with {q, priority, assigned_to}, q stripped", () => {
    const onApply = vi.fn();
    render(<FilterBar onApply={onApply} />);
    const f = bar();
    fireEvent.change(within(f).getByLabelText("Search"), { target: { value: "  leaky sink  " } });
    fireEvent.change(within(f).getByLabelText("Priority"), { target: { value: "urgent" } });
    fireEvent.change(within(f).getByLabelText("Assigned to"), { target: { value: "him" } });
    fireEvent.click(within(f).getByRole("button", { name: "Apply" }));
    expect(onApply).toHaveBeenCalledTimes(1);
    expect(onApply).toHaveBeenCalledWith({ q: "leaky sink", priority: "urgent", assigned_to: "him" });
  });

  it("a blank search is an empty q, and each field is sent on its own", () => {
    const onApply = vi.fn();
    render(<FilterBar onApply={onApply} />);
    const f = bar();
    fireEvent.change(within(f).getByLabelText("Search"), { target: { value: "   " } });
    fireEvent.change(within(f).getByLabelText("Priority"), { target: { value: "low" } });
    fireEvent.submit(f);
    fireEvent.change(within(f).getByLabelText("Priority"), { target: { value: "" } });
    fireEvent.change(within(f).getByLabelText("Assigned to"), { target: { value: "her" } });
    fireEvent.submit(f);
    expect(onApply.mock.calls.map((c) => c[0])).toEqual([
      { q: "", priority: "low", assigned_to: "" },
      { q: "", priority: "", assigned_to: "her" },
    ]);
  });
});

describe("SummaryBadge", () => {
  it("renders span.summary named Summary reading '2 overdue · 1 due today · 5 open'", () => {
    render(<SummaryBadge summary={{ overdue: 2, due_today: 1, open: 5 }} />);
    const s = screen.getByLabelText("Summary");
    expect(s.tagName).toBe("SPAN");
    expect(s).toHaveClass("summary");
    expect(s.textContent).toBe("2 overdue · 1 due today · 5 open");
  });

  it("has the class alert when overdue is more than 0", () => {
    render(<SummaryBadge summary={{ overdue: 1, due_today: 0, open: 1 }} />);
    expect(screen.getByLabelText("Summary")).toHaveClass("summary", "alert");
  });

  it("has no class alert when nothing is overdue, and shows the numbers as given", () => {
    render(<SummaryBadge summary={{ overdue: 0, due_today: 3, open: 7 }} />);
    const s = screen.getByLabelText("Summary");
    expect(s).toHaveClass("summary");
    expect(s).not.toHaveClass("alert");
    expect(s.textContent).toBe("0 overdue · 3 due today · 7 open");
  });

  it("shows zeros", () => {
    render(<SummaryBadge summary={{ overdue: 0, due_today: 0, open: 0 }} />);
    expect(screen.getByLabelText("Summary").textContent).toBe("0 overdue · 0 due today · 0 open");
  });
});
