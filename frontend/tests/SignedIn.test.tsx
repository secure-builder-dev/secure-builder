// GD-2h: fetchMe in frontend/src/api.ts, and frontend/src/App.tsx shows who is signed in.
import "@testing-library/jest-dom/vitest";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import App from "../src/App";
import { fetchMe } from "../src/api";
import { mockApi, region, signIn } from "./helpers";

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("fetchMe", () => {
  it("sends GET /api/me with the bearer token and returns {user}", async () => {
    const api = mockApi({ "GET /api/me": { body: { user: "him" } } });
    await expect(fetchMe("tok-m")).resolves.toEqual({ user: "him" });
    expect(api.calls("GET /api/me")[0].headers["authorization"]).toBe("Bearer tok-m");
  });

  it("throws Error(status) on a non-ok answer", async () => {
    mockApi({ "GET /api/me": { status: 401, body: {} } });
    await expect(fetchMe("t")).rejects.toThrow(new Error("401"));
  });
});

describe("App: signed in", () => {
  it.each([["her", "him"], ["him", "her"]])("as %s: Signed in as %s in the top bar, New ticket for the other", async (me, other) => {
    mockApi({ "GET /api/me": { body: { user: me } } });
    render(<App />);
    await signIn();
    const who = within(screen.getByRole("banner")).getByText(`Signed in as ${me}`);
    expect(who).toHaveClass("whoami");
    expect(within(region("New ticket")).getByRole("heading", { level: 2 }).textContent).toBe(`New ticket for ${other}`);
  });

  it("shows no Signed in text before Load", () => {
    mockApi();
    render(<App />);
    expect(screen.queryByText(/Signed in as/)).toBeNull();
    expect(document.querySelector(".whoami")).toBeNull();
  });

  it("a failed /api/me shows no Signed in text, a plain New ticket heading, and no error", async () => {
    mockApi({ "GET /api/me": { status: 500, body: {} } });
    render(<App />);
    await signIn();
    expect(screen.queryByText(/Signed in as/)).toBeNull();
    expect(within(region("New ticket")).getByRole("heading", { level: 2 }).textContent).toBe("New ticket");
    expect(screen.queryByRole("alert")).toBeNull();
    expect(region("My board")).toBeInTheDocument();
  });

  it("a malformed /api/me answer is treated like a failed one", async () => {
    mockApi({ "GET /api/me": { body: { user: "someone" } } });
    render(<App />);
    await signIn();
    expect(screen.queryByText(/Signed in as/)).toBeNull();
    expect(within(region("New ticket")).getByRole("heading", { level: 2 }).textContent).toBe("New ticket");
  });
});
