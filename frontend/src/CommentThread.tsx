import React, { useState, FormEvent } from "react";
import type { CommentOut } from "./types";

interface CommentThreadProps {
  comments: CommentOut[];
  onAdd: (body: string) => void;
}

export default function CommentThread({ comments, onAdd }: CommentThreadProps) {
  const [text, setText] = useState("");

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = text.trim();
    if (trimmed) {
      onAdd(trimmed);
    }
    setText("");
  };

  return (
    <div className="comment-thread" role="region" aria-label="Comment Thread">
      {comments.length > 0 ? (
        <ol className="comments" aria-label="Comments">
          {comments.map((c) => (
            <li key={c.id} className="comment">
              <span className="comment-author">{c.author}</span>
              <p className="comment-body">{c.body}</p>
            </li>
          ))}
        </ol>
      ) : (
        <p className="empty">No comments yet</p>
      )}
      <form className="comment-form" onSubmit={handleSubmit}>
        <label>
          Comment
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
        </label>
        <button type="submit">Add comment</button>
      </form>
    </div>
  );
}
