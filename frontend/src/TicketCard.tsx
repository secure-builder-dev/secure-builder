import type { ReactNode } from "react";
import type { Ticket } from "./types";

interface TicketCardProps {
  ticket: Ticket;
  children?: ReactNode;
}

export default function TicketCard({ ticket, children }: TicketCardProps) {
  const className = ticket.group === 0 ? "card urgent" : "card";
  return (
    <article className={className} aria-label={ticket.title}>
      <h3 className="card-title">{ticket.title}</h3>
      <div className="card-meta">
        <span className={`badge priority-${ticket.priority}`}>{ticket.priority}</span>
        {ticket.due && <span className="due">due {ticket.due}</span>}
        <span className={`pill status-${ticket.status}`}>{ticket.status.replace(/_/g, " ")}</span>
        <span className="who">for {ticket.assigned_to}</span>
      </div>
      {children && <div className="card-actions">{children}</div>}
    </article>
  );
}
