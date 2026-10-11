import React, { useState } from 'react';

export interface Ticket {
  details: string;
  filed_by: string;
  assigned_to: string;
  created_at: string;
}

interface HoverCardProps {
  ticket: Ticket;
  children: React.ReactNode;
}

export default function HoverCard({ ticket, children }: HoverCardProps) {
  const [showTooltip, setShowTooltip] = useState(false);

  return (
    <span
      className="hover-target"
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
      onFocus={() => setShowTooltip(true)}
      onBlur={() => setShowTooltip(false)}
    >
      {children}
      {showTooltip && (
        <div role="tooltip" className="hover-card">
          <div>{ticket.details || 'No details'}</div>
          <div>Filed by {ticket.filed_by}</div>
          <div>Assigned to {ticket.assigned_to}</div>
          <div>Created {ticket.created_at.slice(0, 10)}</div>
        </div>
      )}
    </span>
  );
}
