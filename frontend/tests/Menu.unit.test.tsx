import "@testing-library/jest-dom/vitest";
import { render, fireEvent, cleanup } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import Menu from "../src/Menu";


afterEach(() => {
  cleanup();
});

test("rendersMenuButtonClosedInitially", () => {
  const { queryByRole, queryByLabelText } = render(<Menu onDirections={() => {}} />);
  const button = queryByRole("button", { name: /menu/i });
  expect(button).toBeInTheDocument();
  expect(button).toHaveClass("menu-button");
  expect(button).toHaveAttribute("aria-expanded", "false");
  // nav should not be in the document when closed
  const nav = queryByLabelText("Main menu");
  expect(nav).not.toBeInTheDocument();
});

test("togglesMenuOpenAndShowsDirectionsButton", () => {
  const { getByRole, queryByLabelText } = render(<Menu onDirections={() => {}} />);
  const menuButton = getByRole("button", { name: /menu/i });
  // open menu
  fireEvent.click(menuButton);
  expect(menuButton).toHaveAttribute("aria-expanded", "true");
  const nav = queryByLabelText("Main menu");
  expect(nav).toBeInTheDocument();
  expect(nav).toHaveClass("menu");
  const directionsButton = getByRole("button", { name: /directions/i });
  expect(directionsButton).toBeInTheDocument();
});

test("clickDirectionsClosesMenuAndCallsCallback", () => {
  const onDirections = vi.fn();
  const { getByRole, queryByLabelText } = render(<Menu onDirections={onDirections} />);
  const menuButton = getByRole("button", { name: /menu/i });
  // open menu first
  fireEvent.click(menuButton);
  expect(menuButton).toHaveAttribute("aria-expanded", "true");
  const directionsButton = getByRole("button", { name: /directions/i });
  // click Directions
  fireEvent.click(directionsButton);
  // callback called once
  expect(onDirections).toHaveBeenCalledTimes(1);
  // menu should be closed again
  expect(menuButton).toHaveAttribute("aria-expanded", "false");
  const nav = queryByLabelText("Main menu");
  expect(nav).not.toBeInTheDocument();
});
