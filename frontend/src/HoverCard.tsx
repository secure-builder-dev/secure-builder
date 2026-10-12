import React, { useState } from "react";
import type { Ticket } from "./types";

interface HoverCardProps {
  ticket: Ticket;
  children: React.ReactNode;
}

export default function HoverCard({ ticket, children }: HoverCardProps) {
  const [showTooltip, setShowTooltip] = useState(false);

  return (
    <span
      className="hover-target"
      tabIndex={0}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
      onFocus={() => setShowTooltip(true)}
      onBlur={() => setShowTooltip(false)}
    >
      {children}
      {showTooltip && (
        <div role="tooltip" className="hover-card">
          <p>{ticket.details || "No details"}</p>
          <p>Filed by {ticket.filed_by}</p>
          <p>Assigned to {ticket.assigned_to}</p>
          <p>Created {ticket.created_at.slice(0, 10)}</p>
        </div>
      )}
    </span>
  );
}