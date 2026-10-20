import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { test, expect, afterEach } from "vitest";
import FilterBar from "../src/FilterBar";

afterEach(() => {
  cleanup();
});

test("test_filter_bar_renders_correctly", () => {
  const onApply = vi.fn();
  render(<FilterBar onApply={onApply} />);

  const form = screen.getByRole("search", { name: /filter household board/i });
  expect(form).toBeInTheDocument();
  expect(form).toHaveClass("filter-bar");

  // Search field
  const searchInput = screen.getByLabelText(/search/i);
  expect(searchInput).toBeInTheDocument();
  expect(searchInput).toHaveAttribute("type", "text");

  // Priority select
  const prioritySelect = screen.getByLabelText(/priority/i);
  expect(prioritySelect).toBeInTheDocument();
  expect(prioritySelect).toHaveTagName("select");
  const priorityOptions = Array.from(prioritySelect.options).map(o => o.text);
  expect(priorityOptions).toEqual(["Any", "low", "normal", "urgent"]);

  // Assigned to select
  const assignedSelect = screen.getByLabelText(/assigned to/i);
  expect(assignedSelect).toBeInTheDocument();
  expect(assignedSelect).toHaveTagName("select");
  const assignedOptions = Array.from(assignedSelect.options).map(o => o.text);
  expect(assignedOptions).toEqual(["Anyone", "her", "him"]);

  // Apply button
  const applyBtn = screen.getByRole("button", { name: /apply/i });
  expect(applyBtn).toBeInTheDocument();
  expect(applyBtn).toHaveAttribute("type", "submit");
});

test("test_filter_bar_calls_onApply_with_stripped_values", async () => {
  const onApply = vi.fn();
  render(<FilterBar onApply={onApply} />);

  fireEvent.change(screen.getByLabelText(/search/i), { target: { value: "  foo  " } });
  fireEvent.change(screen.getByLabelText(/priority/i), { target: { value: "low" } });
  fireEvent.change(screen.getByLabelText(/assigned to/i), { target: { value: "him" } });

  fireEvent.click(screen.getByRole("button", { name: /apply/i }));

  expect(onApply).toHaveBeenCalledTimes(1);
  expect(onApply).toHaveBeenCalledWith({ q: "foo", priority: "low", assigned_to: "him" });

  // Empty fields should produce empty strings
  vi.clearAllMocks();
  fireEvent.change(screen.getByLabelText(/search/i), { target: { value: "   " } });
  fireEvent.change(screen.getByLabelText(/priority/i), { target: { value: "" } });
  fireEvent.change(screen.getByLabelText(/assigned to/i), { target: { value: "" } });
  fireEvent.click(screen.getByRole("button", { name: /apply/i }));
  expect(onApply).toHaveBeenCalledWith({ q: "", priority: "", assigned_to: "" });
});
