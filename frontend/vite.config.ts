/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The API runs on 127.0.0.1:8000 (FastAPI); the dev server forwards /api to it.
export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": "http://127.0.0.1:8000" } },
  test: {
    environment: "jsdom",
    include: ["tests/**/*.test.{ts,tsx}"],
    coverage: { provider: "v8", include: ["src/**"], exclude: ["src/main.tsx", "src/vite-env.d.ts"],
                reporter: ["json-summary", "text-summary"], reportsDirectory: "coverage" },
  },
});
