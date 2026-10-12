import React from "react";
import type { Ticket } from "./types";

export default function TicketCard({ ticket, children }: { ticket: Ticket; children?: React.ReactNode }) {
  const priority = ticket.priority;
  const status = ticket.status.replace(/_/g, " ");
  const due = ticket.due;
  const assignedTo = ticket.assigned_to;

  return (
    <article className={`card${ticket.group === 0 ? " urgent" : ""}`} aria-label={ticket.title}>
      <h3 className="card-title">{ticket.title}</h3>
      <div className="card-meta">
        <span className={`badge priority-${priority}`}>{priority}</span>
        {due && <span className="due">due {due}</span>}
        <span className={`pill status-${ticket.status}`}>{status}</span>
        <span className="who">for {assignedTo}</span>
      </div>
      {children && <div className="card-actions">{children}</div>}
    </article>
  );
}