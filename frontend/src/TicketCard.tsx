import type { Ticket } from "./types";
import HoverCard from "./HoverCard";

interface TicketCardProps {
  ticket: Ticket;
  children?: React.ReactNode;
  onOpen?: (ticket: Ticket) => void;
}

export default function TicketCard({ ticket, children, onOpen }: TicketCardProps) {
  const { title, priority, due, status, assigned_to } = ticket;

  const statusText = status.replace("_", " ");

  const handleClick = () => {
    if (onOpen) {
      onOpen(ticket);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (onOpen && e.key === "Enter") {
      onOpen(ticket);
    }
  };

  return (
    <article className={`card${ticket.group === 0 ? " urgent" : ""}${onOpen ? " openable" : ""}`} aria-label={title}>
      <h3 className="card-title" onClick={handleClick} onKeyDown={handleKeyDown}>
        <HoverCard ticket={ticket}>
          {title}
        </HoverCard>
      </h3>
      <div className="card-meta">
        <span className={`badge priority-${priority}`}>{priority}</span>
        {due && <span className="due">due {due}</span>}
        <span className={`pill status-${status}`}>{statusText}</span>
        <span className="who">for {assigned_to}</span>
      </div>
      {children != null && children !== false && (
        <div className="card-actions">
          {children}
        </div>
      )}
    </article>
  );
}
