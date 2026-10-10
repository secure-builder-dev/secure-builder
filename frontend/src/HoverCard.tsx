import React, { useState } from 'react';

type Ticket = {
  details: string;
  filed_by: string;
  assigned_to: string;
  created_at: string;
};

export default function HoverCard({ ticket, children }: { ticket: Ticket; children: React.ReactNode }) {
  const [isVisible, setIsVisible] = useState(false);

  return (
    <span
      className="hover-target"
      onMouseEnter={() => setIsVisible(true)}
      onMouseLeave={() => setIsVisible(false)}
      onFocus={() => setIsVisible(true)}
      onBlur={() => setIsVisible(false)}
    >
      {children}
      {isVisible && (
        <div role="tooltip" className="hover-card">
          <div>{ticket.details || 'No details'}</div>
          <div>Filed by {ticket.filed_by}</div>
          <div>Assigned to {ticket.assigned_to}</div>
          <div>Created {ticket.created_at.substring(0, 10)}</div>
        </div>
      )}
    </span>
  );
}
