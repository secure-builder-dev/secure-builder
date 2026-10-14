import type { Ticket } from "./types";
import HoverCard from "./HoverCard";

interface TicketCardProps {
  ticket: Ticket;
  children?: React.ReactNode;
}

export default function TicketCard({ ticket, children }: TicketCardProps) {
  const { title, priority, due, status, assigned_to } = ticket;

  const statusText = status.replace("_", " ");

  return (
    <article className={`card${ticket.group === 0 ? " urgent" : ""}`} aria-label={title}>
      <h3 className="card-title">
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
