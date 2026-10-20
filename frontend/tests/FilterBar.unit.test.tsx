// FilterBar.unit.test.tsx – tests for FilterBar component (E4)

import "@testing-library/jest-dom/vitest";
import { render, screen, fireEvent, cleanup, afterEach } from "@testing-library/react";
import React from "react";
import { test, expect } from "vitest";

// Component will be imported dynamically in each test

// Ensure each test cleans up the DOM
afterEach(() => cleanup());

// Clause 1: renders the form with correct structure and fields
test("renders_form_with_correct_structure", async () => {
  const { default: FilterBar } = await import("../src/FilterBar");
  const dummy = jest.fn();
  render(<FilterBar onApply={dummy} />);

  // form element with class filter-bar, role search, aria-label
  const form = screen.getByRole("search", { name: /filter household board/i });
  expect(form).toBeInTheDocument();
  expect(form).toHaveClass("filter-bar");

  // labelled fields
  const searchInput = screen.getByLabelText(/search/i);
  expect(searchInput).toBeInTheDocument();
  expect(searchInput).toHaveAttribute("type", "text");

  const prioritySelect = screen.getByLabelText(/priority/i);
  expect(prioritySelect).toBeInTheDocument();
  // options: Any (empty), low, normal, urgent
  const priorityOptions = Array.from(prioritySelect.querySelectorAll("option")).map(o => o.textContent?.trim());
  expect(priorityOptions).toEqual(["Any", "low", "normal", "urgent"]);

  const assignedSelect = screen.getByLabelText(/assigned to/i);
  expect(assignedSelect).toBeInTheDocument();
  const assignedOptions = Array.from(assignedSelect.querySelectorAll("option")).map(o => o.textContent?.trim());
  expect(assignedOptions).toEqual(["Anyone", "her", "him"]);

  const applyButton = screen.getByRole("button", { name: /apply/i });
  expect(applyButton).toBeInTheDocument();
});

// Clause 2: Apply calls onApply with stripped values and empty strings for no filter
test("apply_calls_onApply_with_stripped_values", async () => {
  const { default: FilterBar } = await import("../src/FilterBar");
  const onApply = jest.fn();
  render(<FilterBar onApply={onApply} />);

  const searchInput = screen.getByLabelText(/search/i) as HTMLInputElement;
  const prioritySelect = screen.getByLabelText(/priority/i) as HTMLSelectElement;
  const assignedSelect = screen.getByLabelText(/assigned to/i) as HTMLSelectElement;
  const applyButton = screen.getByRole("button", { name: /apply/i });

  // Fill values with whitespace and selections
  fireEvent.change(searchInput, { target: { value: "  foo bar  " } });
  fireEvent.change(prioritySelect, { target: { value: "low" } });
  fireEvent.change(assignedSelect, { target: { value: "her" } });
  fireEvent.click(applyButton);

  expect(onApply).toHaveBeenCalledTimes(1);
  expect(onApply).toHaveBeenCalledWith({ q: "foo bar", priority: "low", assigned_to: "her" });

  // Reset mock and submit with empty/whitespace values
  onApply.mockReset();
  fireEvent.change(searchInput, { target: { value: "   " } });
  fireEvent.change(prioritySelect, { target: { value: "" } }); // Any
  fireEvent.change(assignedSelect, { target: { value: "" } }); // Anyone
  fireEvent.click(applyButton);

  expect(onApply).toHaveBeenCalledTimes(1);
  expect(onApply).toHaveBeenCalledWith({ q: "", priority: "", assigned_to: "" });
});

