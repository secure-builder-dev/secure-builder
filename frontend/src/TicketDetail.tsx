import { useState, useEffect } from "react";
import type { Ticket, User, CommentOut, TicketEvent } from "./types";
import { fetchComments, fetchHistory, addComment } from "./api";
import CommentThread from "./CommentThread";
import HistoryList from "./HistoryList";

interface TicketDetailProps {
  token: string;
  ticket: Ticket;
  me: User | null;
  onClose: () => void;
  onSaved?: (ticket: Ticket) => void;
}

export default function TicketDetail({
  token,
  ticket,
  me,
  onClose,
}: TicketDetailProps) {
  const [comments, setComments] = useState<CommentOut[]>([]);
  const [events, setEvents] = useState<TicketEvent[]>([]);
  const [addError, setAddError] = useState<string | null>(null);

  useEffect(() => {
    setComments([]);
    setEvents([]);
    setAddError(null);

    fetchComments(token, ticket.id)
      .then((res) => {
        if (res && Array.isArray(res.comments)) {
          setComments(res.comments);
        }
      })
      .catch(() => {
        setComments([]);
      });

    fetchHistory(token, ticket.id)
      .then((res) => {
        if (res && Array.isArray(res.events)) {
          setEvents(res.events);
        }
      })
      .catch(() => {
        setEvents([]);
      });
  }, [token, ticket.id]);

  const handleAddComment = async (body: string) => {
    try {
      const newComment = await addComment(token, ticket.id, body);
      setComments((prev) => [...prev, newComment]);
      setAddError(null);
    } catch {
      setAddError("Could not add the comment");
    }
  };

  const statusText = ticket.status.replace("_", " ");

  return (
    <section className="panel ticket-detail" aria-label="Ticket details">
      <h2>{ticket.title}</h2>
      {ticket.details !== null && ticket.details !== "" && (
        <p className="detail-text">{ticket.details}</p>
      )}
      <div className="card-meta">
        <span className={`badge priority-${ticket.priority}`}>
          {ticket.priority}
        </span>
        {ticket.due && <span className="due">due {ticket.due}</span>}
        <span className={`pill status-${ticket.status}`}>{statusText}</span>
        <span className="who">for {ticket.assigned_to}</span>
      </div>
      {addError && (
        <p role="alert" className="error">
          {addError}
        </p>
      )}
      <h3>Comments</h3>
      <CommentThread comments={comments} onAdd={handleAddComment} />
      <h3>History</h3>
      <HistoryList events={events} />
      <button className="close-detail" onClick={onClose}>
        Close details
      </button>
    </section>
  );
}