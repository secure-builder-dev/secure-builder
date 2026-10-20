import { useState } from "react";
import type { CommentOut } from "./types";

interface Props {
  comments: CommentOut[];
  onAdd(body: string): void;
}

export default function CommentThread({ comments, onAdd }: Props) {
  const [text, setText] = useState("");

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const body = text.trim();
    if (!body) return;
    onAdd(body);
    setText("");
  }

  return (
    <div className="comment-thread">
      {comments.length === 0 ? (
        <p className="empty">No comments yet</p>
      ) : (
        <ol className="comments" aria-label="Comments">
          {comments.map((c) => (
            <li key={c.id} className="comment">
              <span className="comment-author">{c.author}</span>{" "}
              <p className="comment-body">{c.body}</p>
            </li>
          ))}
        </ol>
      )}
      <form className="comment-form" onSubmit={submit}>
        <label>
          Comment
          <textarea value={text} onChange={(e) => setText(e.target.value)} />
        </label>
        <button type="submit">Add comment</button>
      </form>
    </div>
  );
}
