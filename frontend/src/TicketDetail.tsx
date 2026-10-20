import { useEffect, useState } from "react";
import type { CommentOut, Ticket, TicketEvent, User } from "./types";
import { addComment, fetchComments, fetchHistory } from "./api";
import CommentThread from "./CommentThread";
import HistoryList from "./HistoryList";

interface Props {
  token: string;
  ticket: Ticket;
  me: User | null;
  historyTick?: number;
  onClose(): void;
  onSaved?(ticket: Ticket): void;
}

export default function TicketDetail({ token, ticket, me, historyTick = 0, onClose }: Props) {
  const [comments, setComments] = useState<CommentOut[]>([]);
  const [events, setEvents] = useState<TicketEvent[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setComments([]);
    setEvents([]);
    fetchComments(token, ticket.id)
      .then((res) => {
        if (!alive) return;
        const list = res && Array.isArray(res.comments) ? res.comments : [];
        setComments(list);
      })
      .catch(() => {
        if (alive) setComments([]);
      });
    fetchHistory(token, ticket.id)
      .then((res) => {
        if (!alive) return;
        const list = res && Array.isArray(res.events) ? res.events : [];
        setEvents(list);
      })
      .catch(() => {
        if (alive) setEvents([]);
      });
    return () => {
      alive = false;
    };
  }, [token, ticket.id, historyTick]);

  async function onAdd(body: string) {
    setError(null);
    try {
      const c = await addComment(token, ticket.id, body);
      setComments((prev) => [...prev, c]);
    } catch {
      setError("Could not add the comment");
    }
  }

  return (
    <section className="panel ticket-detail" aria-label="Ticket details">
      <h2>{ticket.title}</h2>
      {ticket.details !== "" && <p className="detail-text">{ticket.details}</p>}
      <div className="card-meta">
        <span className={`badge priority-${ticket.priority}`}>{ticket.priority}</span>
        {ticket.due && <span className="due">due {ticket.due}</span>}
        <span className={`pill status-${ticket.status}`}>{ticket.status.replace(/_/g, " ")}</span>
        <span className="who">for {ticket.assigned_to}</span>
      </div>
      <h3>Comments</h3>
      <CommentThread comments={comments} onAdd={onAdd} />
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
