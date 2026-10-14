import { useState } from "react";
import type { CommentOut } from "./types";

interface CommentThreadProps {
  comments: CommentOut[];
  onAdd: (body: string) => void;
}

export default function CommentThread({ comments, onAdd }: CommentThreadProps) {
  const [text, setText] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const stripped = text.trim();
    if (!stripped) return;
    onAdd(stripped);
    setText("");
  };

  return (
    <div className="comment-thread">
      {comments.length === 0 ? (
        <p className="empty">No comments yet</p>
      ) : (
        <ol className="comments" aria-label="Comments">
          {comments.map((c) => (
            <li key={c.id} className="comment">
              <span className="comment-author">{c.author}</span>
              <p className="comment-body">{c.body}</p>
            </li>
          ))}
        </ol>
      )}
      <form className="comment-form" onSubmit={handleSubmit}>
        <label htmlFor="comment-textarea">Comment</label>
        <textarea
          id="comment-textarea"
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <button type="submit">Add comment</button>
      </form>
    </div>
  );
}
