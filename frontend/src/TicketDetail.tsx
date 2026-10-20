import { useEffect, useState } from "react";
import type { CommentOut, Ticket, TicketEvent, User } from "./types";
import { addComment, editTicket, fetchComments, fetchHistory } from "./api";
import CommentThread from "./CommentThread";
import HistoryList from "./HistoryList";
import EditTicketForm from "./EditTicketForm";

interface Props {
  token: string;
  ticket: Ticket;
  me: User | null;
  historyTick?: number;
  onClose(): void;
  onSaved?(ticket: Ticket): void;
}

export default function TicketDetail({ token, ticket, me, historyTick = 0, onClose, onSaved }: Props) {
  const [savedTicket, setSavedTicket] = useState<Ticket | null>(null);
  const shown = savedTicket ?? ticket;
  const [comments, setComments] = useState<CommentOut[]>([]);
  const [events, setEvents] = useState<TicketEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setComments([]);
    fetchComments(token, ticket.id)
      .then((res) => {
        if (!alive) return;
        const list = res && Array.isArray(res.comments) ? res.comments : [];
        setComments(list);
      })
      .catch(() => {
        if (alive) setComments([]);
      });
    return () => {
      alive = false;
    };
  }, [token, ticket.id]);

  useEffect(() => {
    let alive = true;
    setEvents([]);
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
  }, [token, ticket.id, historyTick, savedTicket]);

  async function onAdd(body: string) {
    setError(null);
    try {
      const c = await addComment(token, ticket.id, body);
      setComments((prev) => [...prev, c]);
    } catch {
      setError("Could not add the comment");
    }
  }

  function canEdit() {
    return me !== null && me === shown.filed_by && (shown.status === "open" || shown.status === "acknowledged");
  }

  async function onSave(changes: { title: string; details: string; priority: Ticket["priority"]; due: string | null }) {
    setEditError(null);
    try {
      const answered = await editTicket(token, ticket.id, changes);
      setEditing(false);
      setSavedTicket(answered);
      onSaved?.(answered);
    } catch {
      setEditError("Could not save");
    }
  }

  function resetForNewTicket() {
    setSavedTicket(null);
    setEditing(false);
    setEditError(null);
    setError(null);
  }

  return (
    <section className="panel ticket-detail" aria-label="Ticket details">
      <h2>{shown.title}</h2>
      {shown.details !== "" && <p className="detail-text">{shown.details}</p>}
      <div className="card-meta">
        <span className={`badge priority-${shown.priority}`}>{shown.priority}</span>
        {shown.due && <span className="due">due {shown.due}</span>}
        <span className={`pill status-${shown.status}`}>{shown.status.replace(/_/g, " ")}</span>
        <span className="who">for {shown.assigned_to}</span>
      </div>
      {canEdit() && !editing && (
        <button type="button" onClick={() => setEditing(true)}>Edit</button>
      )}
      {editing && (
        <EditTicketForm
          key={ticket.id}
          ticket={shown}
          onSave={onSave}
          onCancel={() => setEditing(false)}
          error={editError ?? undefined}
        />
      )}
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