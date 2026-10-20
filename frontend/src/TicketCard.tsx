import React, { ReactNode } from "react";
import { Ticket } from "./types";
import HoverCard from "./HoverCard";

interface TicketCardProps {
  ticket: Ticket;
  children?: ReactNode;
  onOpen?: (ticket: Ticket) => void;
}

const TicketCard: React.FC<TicketCardProps> = ({ ticket, children, onOpen }) => {
  const articleClass = ["card"];
  if (ticket.group === 0) {
    articleClass.push("urgent");
  }
  if (onOpen) {
    articleClass.push("openable");
  }

  const statusDisplay = ticket.status.replace(/_/g, " ");

  const hasChildren = React.Children.count(children) > 0;

  const handleOpen = () => {
    if (onOpen) onOpen(ticket);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && onOpen) {
      e.preventDefault();
      onOpen(ticket);
    }
  };

  return (
    <article className={articleClass.join(" ")} aria-label={ticket.title}>
      <h3 className="card-title" onClick={handleOpen} onKeyDown={handleKeyDown}>
        <HoverCard ticket={ticket}>
          {ticket.title}
        </HoverCard>
      </h3>
      <div className="card-meta">
        <span className={`badge priority-${ticket.priority}`}>{ticket.priority}</span>
        {ticket.due && <span className="due">due {ticket.due}</span>}
        <span className={`pill status-${ticket.status}`}>{statusDisplay}</span>
        <span className="who">for {ticket.assigned_to}</span>
      </div>
      {hasChildren && <div className="card-actions">{children}</div>}
    </article>
  );
};

export default TicketCard;
