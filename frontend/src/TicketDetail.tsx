import React, { useEffect, useState } from "react";
import type { Ticket, CommentOut, TicketEvent, User } from "./types";
import CommentThread from "./CommentThread";
import HistoryList from "./HistoryList";
import { fetchComments, fetchHistory, addComment } from "./api";

interface Props {
  token: string;
  ticket: Ticket;
  me: User | null;
  onClose: () => void;
  onSaved?: (ticket: Ticket) => void; // optional, not used in current tests
}

export default function TicketDetail({ token, ticket, me, onClose }: Props) {
  const [comments, setComments] = useState<CommentOut[]>([]);
  const [events, setEvents] = useState<TicketEvent[]>([]);
  const [error, setError] = useState<string | null>(null);

  // fetch comments and history when component mounts or ticket.id changes
  useEffect(() => {
    let cancelled = false;
    // reset state on ticket change
    setComments([]);
    setEvents([]);
    setError(null);

    const loadComments = async () => {
      try {
        const data = await fetchComments(token, ticket.id);
        if (data && Array.isArray(data.comments)) {
          if (!cancelled) setComments(data.comments);
        } else {
          // malformed shape -> empty list
          if (!cancelled) setComments([]);
        }
      } catch (_) {
        if (!cancelled) setComments([]);
      }
    };

    const loadHistory = async () => {
      try {
        const data = await fetchHistory(token, ticket.id);
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
  }, [ticket.id, token]);

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

  // Render meta spans similar to TicketCard
  const statusDisplay = ticket.status.replace(/_/g, " ");

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
