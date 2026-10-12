import React from "react";
import type { Ticket } from "./types";
import HoverCard from "./HoverCard";

interface TicketCardProps {
  ticket: Ticket;
  children?: React.ReactNode;
}

export default function TicketCard({ ticket, children }: TicketCardProps) {
  const { title, priority, due, status, assigned_to } = ticket;
  const hasChildren = children != null && children !== false;

  return (
    <article
      className={`card${ticket.group === 0 ? " urgent" : ""}`}
      aria-label={title}
    >
      <h3 className="card-title">
        <HoverCard ticket={ticket}>
          {title}
        </HoverCard>
      </h3>
      <div className="card-meta">
        <span className={`badge priority-${priority}`}>
          {priority}
        </span>
        {due != null && (
          <span className="due">due {due}</span>
        )}
        <span className={`pill status-${status}`}>
          {status.replace("_", " ")}
        </span>
        <span className="who">for {assigned_to}</span>
      </div>
      {hasChildren && (
        <div className="card-actions">
          {children}
        </div>
      )}
    </article>
  );
}