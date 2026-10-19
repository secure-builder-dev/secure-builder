import React, { ReactNode } from "react";
import type { Ticket } from "./types";

interface TicketCardProps {
  ticket: Ticket;
  children?: ReactNode;
}

/**
 * TicketCard renders a ticket as a card.
 * It follows the design spec used by the unit tests.
 */
export default function TicketCard({ ticket, children }: TicketCardProps) {
  // Determine if we should render the actions container.
  const hasActions = React.Children.toArray(children).some(
    (c) => c !== null && c !== undefined && c !== false,
  );

  const articleClass = ["card", ticket.group === 0 ? "urgent" : null]
    .filter(Boolean)
    .join(" ");

  // Convert status for display (replace '_' with space).
  const displayStatus = ticket.status.replace(/_/g, " ");

  return (
    <article className={articleClass} aria-label={ticket.title}>
      <h3 className="card-title">{ticket.title}</h3>
      <div className="card-meta">
        <span className={`badge priority-${ticket.priority}`}>{ticket.priority}</span>
        {ticket.due && <span className="due">due {ticket.due}</span>}
        <span className={`pill status-${ticket.status}`}>{displayStatus}</span>
        <span className="who">for {ticket.assigned_to}</span>
      </div>
      {hasActions && <div className="card-actions">{children}</div>}
    </article>
  );
}
