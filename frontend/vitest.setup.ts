// Test environment setup (not application code). jest-dom adds the DOM matchers (toHaveAttribute, toBeInTheDocument)
// the acceptance tests use; cleanup unmounts each test's render, which Testing Library only does on its own when
// Vitest globals are on. Without it every test after the first found several "Load" buttons and failed.
import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

afterEach(() => {
  cleanup();
});
