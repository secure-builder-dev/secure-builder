import "@testing-library/jest-dom/vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import CommentThread from "../src/CommentThread";
import HistoryList from "../src/HistoryList";
import { comment, event } from "./helpers";

afterEach(() => {
  document.body.innerHTML = "";
});

// Clause 1: CommentThread renders comments or empty message
describe("CommentThread", () => {
  it("renders div.comment-thread with ol.comments named Comments holding one li.comment per comment", () => {
    const c1 = comment({ id: 1, author: "her", body: "First comment" });
    const c2 = comment({ id: 2, author: "him", body: "Second comment" });

    render(<CommentThread comments={[c1, c2]} onAdd={() => {}} />);

    expect(screen.getByRole("list", { name: "Comments" })).toBeInTheDocument();
    const items = screen.getAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveTextContent("her");
    expect(items[0]).toHaveTextContent("First comment");
    expect(items[1]).toHaveTextContent("him");
    expect(items[1]).toHaveTextContent("Second comment");
  });

  it("renders p.empty with No comments yet when there are none", () => {
    render(<CommentThread comments={[]} onAdd={() => {}} />);

    expect(screen.getByText("No comments yet")).toBeInTheDocument();
    expect(screen.queryByRole("list", { name: "Comments" })).not.toBeInTheDocument();
  });
});

// Clause 2: CommentThread form behavior
describe("CommentThread form", () => {
  it("has a textarea labelled Comment and an Add comment submit button", () => {
    render(<CommentThread comments={[]} onAdd={() => {}} />);

    const label = screen.getByText("Comment");
    expect(label).toBeInTheDocument();
    const textarea = screen.getByRole("textbox") as HTMLTextAreaElement;
    expect(textarea).toBeInTheDocument();
    expect(screen.getByLabelText("Comment")).toBe(textarea);

    const button = screen.getByRole("button", { name: "Add comment" });
    expect(button).toBeInTheDocument();
  });

  it("submitting calls onAdd with the stripped text and empties the field", async () => {
    const user = userEvent.setup();
    const onAdd = vi.fn();

    render(<CommentThread comments={[]} onAdd={onAdd} />);

    const textarea = screen.getByRole("textbox") as HTMLTextAreaElement;
    await user.type(textarea, "  Hello World  ");
    await user.click(screen.getByRole("button", { name: "Add comment" }));

    expect(onAdd).toHaveBeenCalledWith("Hello World");
    expect(textarea.value).toBe("");
  });

  it("blank text calls nothing", async () => {
    const user = userEvent.setup();
    const onAdd = vi.fn();

    render(<CommentThread comments={[]} onAdd={onAdd} />);

    const textarea = screen.getByRole("textbox") as HTMLTextAreaElement;
    await user.type(textarea, "   ");
    await user.click(screen.getByRole("button", { name: "Add comment" }));

    expect(onAdd).not.toHaveBeenCalled();
  });
});

// Clause 3: HistoryList renders events or empty message
describe("HistoryList", () => {
  it("renders ol.history named History with one li per event, oldest first", () => {
    const e1 = event({ id: 1, actor: "her", kind: "filed" });
    const e2 = event({ id: 2, actor: "him", kind: "status", from_status: "open", to_status: "acknowledged" });
    const e3 = event({ id: 3, actor: "her", kind: "edited" });

    render(<HistoryList events={[e1, e2, e3]} />);

    expect(screen.getByRole("list", { name: "History" })).toBeInTheDocument();
    const items = screen.getAllByRole("listitem");
    expect(items).toHaveLength(3);
    expect(items[0]).toHaveTextContent("her filed it");
    expect(items[1]).toHaveTextContent("him moved it from open to acknowledged");
    expect(items[2]).toHaveTextContent("her edited it");
  });

  it("renders statuses with _ as a space (e.g., in progress)", () => {
    const e = event({ id: 1, actor: "him", kind: "status", from_status: "acknowledged", to_status: "in_progress" });

    render(<HistoryList events={[e]} />);

    expect(screen.getByText("him moved it from acknowledged to in progress")).toBeInTheDocument();
  });

  it("renders p.empty with No history when there are none", () => {
    render(<HistoryList events={[]} />);

    expect(screen.getByText("No history")).toBeInTheDocument();
    expect(screen.queryByRole("list", { name: "History" })).not.toBeInTheDocument();
  });
});
