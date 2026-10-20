import React, { FormEvent, useRef } from "react";
import type { CommentOut } from "./types";

interface Props {
  comments: CommentOut[];
  onAdd: (body: string) => void;
}

export default function CommentThread({ comments, onAdd }: Props) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const ta = textareaRef.current;
    if (!ta) return;
    const raw = ta.value;
    const stripped = raw.trim();
    if (stripped.length === 0) {
      // do nothing for blank input
      return;
    }
    onAdd(stripped);
    ta.value = "";
  };

  return (
    <div className="comment-thread">
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
          <textarea ref={textareaRef} />
        </label>
        <button type="submit">Add comment</button>
      </form>
    </div>
  );
}
