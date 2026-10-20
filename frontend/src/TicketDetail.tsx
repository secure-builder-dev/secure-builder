import React, { useEffect, useState } from "react";
import type { Ticket, CommentOut, TicketEvent, User, Priority } from "./types";
import CommentThread from "./CommentThread";
import HistoryList from "./HistoryList";
import EditTicketForm from "./EditTicketForm";
import { fetchComments, fetchHistory, addComment, editTicket } from "./api";

interface Props {
  token: string;
  ticket: Ticket;
  me: User | null;
  onClose: () => void;
  onSaved?: (ticket: Ticket) => void; // optional, not used in current tests
}

export default function TicketDetail({ token, ticket: initialTicket, me, onClose, onSaved }: Props) {
  const [ticket, setTicket] = useState<Ticket>(initialTicket);
  const [comments, setComments] = useState<CommentOut[]>([]);
  const [events, setEvents] = useState<TicketEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [editError, setEditError] = useState<string | null>(null);
  const [editing, setEditing] = useState<boolean>(false);

  // fetch comments and history when component mounts or ticket.id changes
  useEffect(() => {
    let cancelled = false;
    // reset state on ticket change
    setComments([]);
    setEvents([]);
    setError(null);
    setEditError(null);
    setEditing(false);
    setTicket(initialTicket);

    const loadComments = async () => {
      try {
        const data = await fetchComments(token, initialTicket.id);
        if (data && Array.isArray(data.comments)) {
          if (!cancelled) setComments(data.comments);
        } else {
          if (!cancelled) setComments([]);
        }
      } catch (_) {
        if (!cancelled) setComments([]);
      }
    };

    const loadHistory = async () => {
      try {
        const data = await fetchHistory(token, initialTicket.id);
        if (data && Array.isArray(data.events)) {
          if (!cancelled) setEvents(data.events);
        } else {
          if (!cancelled) setEvents([]);
        }
      } catch (_) {
        if (!cancelled) setEvents([]);
      }
    };

    loadComments();
    loadHistory();

    return () => {
      cancelled = true;
    };
  }, [initialTicket.id, token, initialTicket]);

  const handleAddComment = async (body: string) => {
    try {
      const newComment = await addComment(token, ticket.id, body);
      // API returns the comment object directly
      setComments((prev) => [...prev, newComment]);
      setError(null);
    } catch (_) {
      setError("Could not add the comment");
    }
  };

  const handleSaveEdit = async (changes: { title: string; details: string; priority: Priority; due: string | null }) => {
    try {
      const updated = await editTicket(token, ticket.id, changes);
      setTicket(updated);
      setEditing(false);
      setEditError(null);
      // refetch history after successful edit
      const hist = await fetchHistory(token, ticket.id);
      if (hist && Array.isArray(hist.events)) {
        setEvents(hist.events);
      } else {
        setEvents([]);
      }
      if (onSaved) onSaved(updated);
    } catch (_) {
      setEditError("Could not save");
    }
  };

  // Render meta spans similar to TicketCard
  const statusDisplay = ticket.status.replace(/_/g, " ");

  const showEditButton =
    me !== null && me === ticket.filed_by && (ticket.status === "open" || ticket.status === "acknowledged");

  return (
    <section className="panel ticket-detail" aria-label="Ticket details">
      <h2>{ticket.title}</h2>
      {ticket.details && ticket.details.length > 0 && (
        <p className="detail-text">{ticket.details}</p>
      )}
      <div className="card-meta">
        <span className={`badge priority-${ticket.priority}`}>{ticket.priority}</span>
        {ticket.due && <span className="due">due {ticket.due}</span>}
        <span className={`pill status-${ticket.status}`}>{statusDisplay}</span>
        <span className="who">for {ticket.assigned_to}</span>
      </div>
      {showEditButton && !editing && (
        <button onClick={() => setEditing(true)}>Edit</button>
      )}
      {editing && (
        <EditTicketForm
          ticket={ticket}
          onSave={handleSaveEdit}
          onCancel={() => setEditing(false)}
          error={editError ?? undefined}
        />
      )}
      <h3>Comments</h3>
      <CommentThread comments={comments} onAdd={handleAddComment} />
      <h3>History</h3>
      <HistoryList events={events} />
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <button className="close-detail" onClick={onClose}>
        Close details
      </button>
    </section>
  );
}
