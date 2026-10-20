import type { ReactNode } from "react";
import type { Ticket } from "./types";
import HoverCard from "./HoverCard";

interface TicketCardProps {
  ticket: Ticket;
  children?: ReactNode;
  onOpen?: (ticket: Ticket) => void;
}

export default function TicketCard({ ticket, children, onOpen }: TicketCardProps) {
  const className = ["card", ticket.group === 0 ? "urgent" : null, onOpen ? "openable" : null]
    .filter(Boolean)
    .join(" ");
  return (
    <article className={className} aria-label={ticket.title}>
      <h3
        className="card-title"
        onClick={onOpen ? () => onOpen(ticket) : undefined}
        onKeyDown={onOpen ? (e) => { if (e.key === "Enter") onOpen(ticket); } : undefined}
      >
        <HoverCard ticket={ticket}>{ticket.title}</HoverCard>
      </h3>
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