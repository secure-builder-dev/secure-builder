import React, { ReactNode } from "react";
import type { Ticket } from "./types";
import HoverCard from "./HoverCard";

interface TicketCardProps {
  ticket: Ticket;
  children?: ReactNode;
  /**
   * Optional callback invoked when the card is opened.
   * When provided the card gets the "openable" class and clicking the title
   * or pressing Enter while the hover target is focused will call this function
   * with the ticket.
   */
  onOpen?: (ticket: Ticket) => void;
}

/**
 * TicketCard renders a ticket as a card.
 * It follows the design spec used by the unit tests.
 */
export default function TicketCard({ ticket, children, onOpen }: TicketCardProps) {
  // Determine if we should render the actions container.
  const hasActions = React.Children.toArray(children).some(
    (c) => c !== null && c !== undefined && c !== false,
  );

  const articleClass = [
    "card",
    ticket.group === 0 ? "urgent" : null,
    onOpen ? "openable" : null,
  ]
    .filter(Boolean)
    .join(" ");

  // Convert status for display (replace '_' with space).
  const displayStatus = ticket.status.replace(/_/g, " ");

  const handleClick = () => {
    if (onOpen) onOpen(ticket);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && onOpen) {
      onOpen(ticket);
    }
  };

  return (
    <article className={articleClass} aria-label={ticket.title}>
      {/* Wrapper to capture keydown when the hover target is focused */}
      <div onKeyDown={handleKeyDown}>
        <HoverCard ticket={ticket}>
          <h3 className="card-title" onClick={handleClick}>
            {ticket.title}
          </h3>
        </HoverCard>
      </div>
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
