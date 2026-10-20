import React, { useEffect, useState } from "react";
import type { Ticket, CommentOut, TicketEvent, TicketEdit } from "./types";
import EditTicketForm from "./EditTicketForm";
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
  // Local mutable copy of the ticket so we can reflect edits without parent re‑render
  const [currentTicket, setCurrentTicket] = useState<Ticket>(ticket);
  const [comments, setComments] = useState<CommentOut[]>([]);
  const [events, setEvents] = useState<TicketEvent[]>([]);
  const [addError, setAddError] = useState<string>("");
  const [editMode, setEditMode] = useState<boolean>(false);
  const [editError, setEditError] = useState<string>("");

  // Keep local ticket in sync when the prop changes (e.g., parent updates)
  useEffect(() => {
    setCurrentTicket(ticket);
  }, [ticket]);

  // Fetch comments and history whenever the component mounts or the ticket id changes
  useEffect(() => {
    // reset state for a new ticket
    setComments([]);
    setEvents([]);
    setAddError("");
    setEditError("");
    setEditMode(false);

    // fetch comments
    api
      .fetchComments(token, currentTicket.id)
      .then((resp) => setComments(resp.comments))
      .catch(() => setComments([]));

    // fetch history
    api
      .fetchHistory(token, currentTicket.id)
      .then((resp) => setEvents(resp.events))
      .catch(() => setEvents([]));
  }, [token, currentTicket.id, currentTicket.status]);

  const handleAddComment = async (body: string) => {
    try {
      const newComment = await api.addComment(token, currentTicket.id, body);
      setComments((prev) => [...prev, newComment]);
      setAddError("");
    } catch (e) {
      setAddError("Could not add the comment");
    }
  };

  const handleEditSave = async (changes: TicketEdit) => {
    try {
      const updated = await api.editTicket(token, currentTicket.id, changes);
      // Update local ticket and clear edit mode
      setCurrentTicket(updated);
      setEditMode(false);
      setEditError("");
      // Refetch history after successful edit
      api.fetchHistory(token, updated.id).then((resp) => setEvents(resp.events)).catch(() => setEvents([]));
      if (onSaved) onSaved(updated);
    } catch (e) {
      setEditError("Could not save");
    }
  };

  // Render status with spaces instead of underscores
  const displayStatus = currentTicket.status.replace(/_/g, " ");

  // Determine if the Edit button should be shown
  const showEditButton =
    me === currentTicket.filed_by && (currentTicket.status === "open" || currentTicket.status === "acknowledged");

  return (
    <section
      className="panel ticket-detail"
      role="region"
      aria-label="Ticket details"
    >
      <h2>{currentTicket.title}</h2>
      {currentTicket.details && currentTicket.details.trim() !== "" && (
        <p className="detail-text">{currentTicket.details}</p>
      )}
      <div className="card-meta">
        <span className={`badge priority-${currentTicket.priority}`}>{currentTicket.priority}</span>
        {currentTicket.due && <span className="due">due {currentTicket.due}</span>}
        <span className={`pill status-${currentTicket.status}`}>{displayStatus}</span>
        <span className="who">for {currentTicket.assigned_to}</span>
      </div>
      {showEditButton && !editMode && (
        <button className="edit-button" onClick={() => setEditMode(true)}>
          Edit
        </button>
      )}
      {editMode && (
        <EditTicketForm
          ticket={currentTicket}
          onSave={handleEditSave}
          onCancel={() => { setEditMode(false); setEditError(""); }}
          error={editError || undefined}
        />
      )}
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
