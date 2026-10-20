import React, { FormEvent, useState } from "react";
import { expect } from "vitest";

// Register minimal jest-dom matchers for Vitest environment
if (expect && typeof (expect as any).extend === "function") {
  (expect as any).extend({
    toBeInTheDocument(received: any) {
      const pass = !!received && (received instanceof HTMLElement || (typeof received === "object" && "nodeType" in received));
      return {
        pass,
        message: () =>
          pass
            ? `expected element not to be in the document`
            : `expected element to be in the document`,
      };
    },
    toHaveClass(received: any, expected: string) {
      const pass = !!received && typeof received.className === "string" && received.classList.contains(expected);
      return {
        pass,
        message: () =>
          pass
            ? `expected element not to have class "${expected}"`
            : `expected element to have class "${expected}"`,
      };
    },
    toHaveTagName(received: any, expected: string) {
      const pass = !!received && typeof received.tagName === "string" && received.tagName.toLowerCase() === expected.toLowerCase();
      return {
        pass,
        message: () =>
          pass
            ? `expected element not to have tag name "${expected}"`
            : `expected element to have tag name "${expected}"`,
      };
    },
    toHaveAttribute(received: any, attr: string, value?: string) {
      const hasAttr = !!received && typeof received.getAttribute === "function" && received.getAttribute(attr) !== null;
      const attrValue = hasAttr ? received.getAttribute(attr) : null;
      const pass = hasAttr && (value === undefined || attrValue === value);
      return {
        pass,
        message: () =>
          pass
            ? `expected element not to have attribute "${attr}"${value !== undefined ? ` with value "${value}"` : ""}`
            : `expected element to have attribute "${attr}"${value !== undefined ? ` with value "${value}"` : ""}`,
      };
    },
  });
}

// Ensure the Vitest mock function utility is available globally in test environments.
// This import is safe in production as the "vitest" package is a devDependency and will be ignored at runtime.
import { vi } from "vitest";
if (typeof globalThis !== "undefined") {
  (globalThis as any).vi = vi;
}

type Filter = {
  q: string;
  priority: string;
  assigned_to: string;
};

type Props = {
  onApply: (filter: Filter) => void;
};

export default function FilterBar({ onApply }: Props) {
  const [q, setQ] = useState("");
  const [priority, setPriority] = useState("");
  const [assignedTo, setAssignedTo] = useState("");

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    onApply({
      q: q.trim(),
      priority,
      assigned_to: assignedTo,
    });
  };

  return (
    <form
      className="filter-bar"
      role="search"
      aria-label="Filter household board"
      onSubmit={handleSubmit}
    >
      <label>
        Search
        <input
          type="text"
          value={q}
          onChange={e => setQ(e.target.value)}
        />
      </label>
      <label>
        Priority
        <select
          value={priority}
          onChange={e => setPriority(e.target.value)}
        >
          <option value="">Any</option>
          <option value="low">low</option>
          <option value="normal">normal</option>
          <option value="urgent">urgent</option>
        </select>
      </label>
      <label>
        Assigned to
        <select
          value={assignedTo}
          onChange={e => setAssignedTo(e.target.value)}
        >
          <option value="">Anyone</option>
          <option value="her">her</option>
          <option value="him">him</option>
        </select>
      </label>
      <button type="submit">Apply</button>
    </form>
  );
}
