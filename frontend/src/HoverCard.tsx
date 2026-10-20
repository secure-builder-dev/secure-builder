import { useState } from "react";
import type { ReactNode } from "react";
import type { Ticket } from "./types";

interface HoverCardProps {
  ticket: Ticket;
  children: ReactNode;
}

export default function HoverCard({ ticket, children }: HoverCardProps) {
  const [shown, setShown] = useState(false);

  return (
    <span
      className="hover-target"
      tabIndex={0}
      onMouseEnter={() => setShown(true)}
      onMouseLeave={() => setShown(false)}
      onFocus={() => setShown(true)}
      onBlur={() => setShown(false)}
    >
      {children}
      {shown && (
        <div role="tooltip" className="hover-card">
          <p>{ticket.details ? ticket.details : "No details"}</p>
          <p>Filed by {ticket.filed_by}</p>
          <p>Assigned to {ticket.assigned_to}</p>
          <p>Created {ticket.created_at.slice(0, 10)}</p>
        </div>
      )}
    </span>
  );
}
