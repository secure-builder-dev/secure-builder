// TO-3g: frontend/src/CommentThread.tsx and frontend/src/HistoryList.tsx
import "@testing-library/jest-dom/vitest";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import CommentThread from "../src/CommentThread";
import HistoryList from "../src/HistoryList";
import { comment, event } from "./helpers";

afterEach(cleanup);

const C = [
  comment({ author: "her", body: "Please fix it soon" }),
  comment({ author: "him", body: "On it" }),
];

function thread(): HTMLElement {
  return document.querySelector(".comment-thread") as HTMLElement;
}

function field(): HTMLTextAreaElement {
  return screen.getByRole("textbox", { name: "Comment" }) as HTMLTextAreaElement;
}

describe("CommentThread", () => {
  it("renders a div.comment-thread holding an ol.comments named Comments", () => {
    render(<CommentThread comments={C} onAdd={() => {}} />);
    const root = thread();
    expect(root).not.toBeNull();
    expect(root.tagName).toBe("DIV");
    const list = screen.getByRole("list", { name: "Comments" });
    expect(list.tagName).toBe("OL");
    expect(list).toHaveClass("comments");
    expect(root.contains(list)).toBe(true);
  });

  it("holds one li.comment per comment, in order, with the author and the text", () => {
    render(<CommentThread comments={C} onAdd={() => {}} />);
    const items = within(screen.getByRole("list", { name: "Comments" })).getAllByRole("listitem");
    expect(items).toHaveLength(2);
    items.forEach((li) => {
      expect(li.tagName).toBe("LI");
      expect(li).toHaveClass("comment");
    });
    const author0 = items[0].querySelector(".comment-author")!;
    expect(author0.tagName).toBe("SPAN");
    expect(author0.textContent).toBe("her");
    const body0 = items[0].querySelector(".comment-body")!;
    expect(body0.tagName).toBe("P");
    expect(body0.textContent).toBe("Please fix it soon");
    expect(items[1].querySelector(".comment-author")!.textContent).toBe("him");
    expect(items[1].querySelector(".comment-body")!.textContent).toBe("On it");
  });

  it("shows p.empty with No comments yet when there are none", () => {
    render(<CommentThread comments={[]} onAdd={() => {}} />);
    const empty = within(thread()).getByText("No comments yet");
    expect(empty.tagName).toBe("P");
    expect(empty).toHaveClass("empty");
    expect(thread().querySelectorAll("li.comment")).toHaveLength(0);
  });

  it("does not show No comments yet when there are comments", () => {
    render(<CommentThread comments={C} onAdd={() => {}} />);
    expect(screen.queryByText("No comments yet")).toBeNull();
  });

  it("has a form.comment-form with a textarea labelled Comment and an Add comment submit button", () => {
    render(<CommentThread comments={[]} onAdd={() => {}} />);
    const form = thread().querySelector("form.comment-form") as HTMLFormElement;
    expect(form).not.toBeNull();
    const ta = field();
    expect(ta.tagName).toBe("TEXTAREA");
    expect(form.contains(ta)).toBe(true);
    const btn = within(form).getByRole("button", { name: "Add comment" });
    expect(btn).toHaveAttribute("type", "submit");
  });

  it("submitting calls onAdd with the stripped text and empties the field", () => {
    const onAdd = vi.fn();
    render(<CommentThread comments={C} onAdd={onAdd} />);
    fireEvent.change(field(), { target: { value: "   Thanks!  \n" } });
    fireEvent.click(screen.getByRole("button", { name: "Add comment" }));
    expect(onAdd).toHaveBeenCalledTimes(1);
    expect(onAdd).toHaveBeenCalledWith("Thanks!");
    expect(field().value).toBe("");
  });

  it("submitting the form itself calls onAdd too", () => {
    const onAdd = vi.fn();
    render(<CommentThread comments={[]} onAdd={onAdd} />);
    fireEvent.change(field(), { target: { value: "Hello" } });
    fireEvent.submit(thread().querySelector("form.comment-form")!);
    expect(onAdd).toHaveBeenCalledWith("Hello");
  });

  it("blank text calls nothing", () => {
    const onAdd = vi.fn();
    render(<CommentThread comments={[]} onAdd={onAdd} />);
    fireEvent.click(screen.getByRole("button", { name: "Add comment" }));
    fireEvent.change(field(), { target: { value: "   \n\t " } });
    fireEvent.click(screen.getByRole("button", { name: "Add comment" }));
    expect(onAdd).not.toHaveBeenCalled();
  });
});

describe("HistoryList", () => {
  it("renders an ol.history named History with one li per event, in the given (oldest first) order", () => {
    const events = [
      event({ actor: "her", kind: "filed", from_status: null, to_status: "open" }),
      event({ actor: "him", kind: "status", from_status: "open", to_status: "acknowledged" }),
      event({ actor: "her", kind: "edited", from_status: null, to_status: null }),
    ];
    render(<HistoryList events={events} />);
    const list = screen.getByRole("list", { name: "History" });
    expect(list.tagName).toBe("OL");
    expect(list).toHaveClass("history");
    const items = within(list).getAllByRole("listitem");
    expect(items.map((li) => li.textContent)).toEqual([
      "her filed it",
      "him moved it from open to acknowledged",
      "her edited it",
    ]);
  });

  it("shows a status with _ as a space", () => {
    const events = [
      event({ actor: "him", kind: "status", from_status: "acknowledged", to_status: "in_progress" }),
      event({ actor: "him", kind: "status", from_status: "in_progress", to_status: "done" }),
    ];
    render(<HistoryList events={events} />);
    const items = within(screen.getByRole("list", { name: "History" })).getAllByRole("listitem");
    expect(items.map((li) => li.textContent)).toEqual([
      "him moved it from acknowledged to in progress",
      "him moved it from in progress to done",
    ]);
  });

  it("names the actor of each event", () => {
    const events = [
      event({ actor: "him", kind: "filed", to_status: "open" }),
      event({ actor: "her", kind: "status", from_status: "done", to_status: "closed" }),
      event({ actor: "him", kind: "edited", to_status: null }),
    ];
    render(<HistoryList events={events} />);
    const items = within(screen.getByRole("list", { name: "History" })).getAllByRole("listitem");
    expect(items.map((li) => li.textContent)).toEqual([
      "him filed it",
      "her moved it from done to closed",
      "him edited it",
    ]);
  });

  it("shows p.empty with No history when there are no events", () => {
    const { container } = render(<HistoryList events={[]} />);
    const empty = screen.getByText("No history");
    expect(empty.tagName).toBe("P");
    expect(empty).toHaveClass("empty");
    expect(container.querySelectorAll("li")).toHaveLength(0);
  });
});
