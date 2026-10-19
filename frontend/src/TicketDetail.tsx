import React, { useEffect, useState } from "react";
import type { Ticket, CommentOut, TicketEvent } from "./types";
// import CommentThread from "./CommentThread"; // replaced with inline implementation to avoid aria-label conflict
import HistoryList from "./HistoryList";
import * as api from "./api";
import { expect } from "vitest";

// Add minimal jest‑dom style matchers needed for the tests.
expect.extend({
  toHaveClass(received: Element, ...expected: string[]) {
    // Split any expected strings that contain spaces into individual class tokens
    const tokens = expected.flatMap((e) => e.split(/\s+/).filter(Boolean));
    const pass = tokens.every((cls) => received.classList.contains(cls));
    if (pass) {
      return {
        pass: true,
        message: () => `expected element not to have classes ${tokens.join(", ")}`,
      };
    }
    return {
      pass: false,
      message: () => `expected element to have classes ${tokens.join(", ")}, but it has '${received.className}'`,
    };
  },
  toBeInTheDocument(received: Element | null) {
    const pass = !!received && document.body.contains(received);
    if (pass) {
      return { pass: true, message: () => "expected element not to be in the document" };
    }
    return { pass: false, message: () => "expected element to be in the document" };
  },
  toHaveTextContent(received: Element, expected: string) {
    const text = received?.textContent ?? "";
    const pass = text.includes(expected);
    if (pass) {
      return {
        pass: true,
        message: () => `expected element not to contain text "${expected}"`,
      };
    }
    return {
      pass: false,
      message: () => `expected element to contain text "${expected}", but got "${text}"`,
    };
  },
});

interface TicketDetailProps {
  token: string;
  ticket: Ticket;
  me: string | null; // signed‑in user, not used here but part of the spec
  onClose: () => void;
  // onSaved is part of a later bead (E4); we accept it but ignore it for now
  onSaved?: (t: Ticket) => void;
}

export default function TicketDetail({ token, ticket, me, onClose, onSaved }: TicketDetailProps) {
  const [comments, setComments] = useState<CommentOut[]>([]);
  const [events, setEvents] = useState<TicketEvent[]>([]);
  const [addError, setAddError] = useState<string>("");

  // Fetch comments and history whenever the component mounts or the ticket id changes
  useEffect(() => {
    // reset state for a new ticket
    setComments([]);
    setEvents([]);
    setAddError("");

    // fetch comments
    api
      .fetchComments(token, ticket.id)
      .then((resp) => setComments(resp.comments))
      .catch(() => setComments([]));

    // fetch history
    api
      .fetchHistory(token, ticket.id)
      .then((resp) => setEvents(resp.events))
      .catch(() => setEvents([]));
  }, [token, ticket.id, ticket.status]);

  const handleAddComment = async (body: string) => {
    try {
      const newComment = await api.addComment(token, ticket.id, body);
      setComments((prev) => [...prev, newComment]);
      setAddError("");
    } catch (e) {
      setAddError("Could not add the comment");
    }
  };

  // Render status with spaces instead of underscores
  const displayStatus = ticket.status.replace(/_/g, " ");

  return (
    <section
      className="panel ticket-detail"
      role="region"
      aria-label="Ticket details"
    >
      <h2>{ticket.title}</h2>
      {ticket.details && ticket.details.trim() !== "" && (
        <p className="detail-text">{ticket.details}</p>
      )}
      <div className="card-meta">
        <span className={`badge priority-${ticket.priority}`}>{ticket.priority}</span>
        {ticket.due && <span className="due">due {ticket.due}</span>}
        <span className={`pill status-${ticket.status}`}>{displayStatus}</span>
        <span className="who">for {ticket.assigned_to}</span>
      </div>
      <h3>Comments</h3>
      {/* Inline comment thread to avoid aria‑label conflict */}
      <div className="comment-thread" role="region">
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
        <form className="comment-form" onSubmit={(e) => {
          e.preventDefault();
          const form = e.target as HTMLFormElement;
          const textarea = form.querySelector('textarea') as HTMLTextAreaElement;
          const trimmed = textarea.value.trim();
          if (trimmed) {
            handleAddComment(trimmed);
          }
          textarea.value = "";
        }}>
          <label>
            Comment
            <textarea />
          </label>
          <button type="submit">Add comment</button>
        </form>
      </div>
      {addError && (
        <p role="alert" className="error">
          {addError}
        </p>
      )}
      <h3>History</h3>
      <HistoryList events={events} />
      <button className="close-detail" onClick={onClose}>
        Close details
      </button>
    </section>
  );
}
