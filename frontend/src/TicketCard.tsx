import React from 'react';
import type { Ticket } from './types';

const TicketCard = ({ ticket, children }: { ticket: Ticket; children?: React.ReactNode }) => {
  const statusText = ticket.status.replace(/_/g, ' ');

  return (
    <article className={`card ${ticket.group === 0 ? 'urgent' : ''}`} aria-label={ticket.title}>
      <h3 className="card-title">{ticket.title}</h3>
      <div className="card-meta">
        <span className={`badge priority-${ticket.priority}`}>{ticket.priority}</span>
        {ticket.due && <span className="due">due {ticket.due}</span>}
        <span className={`pill status-${ticket.status}`}>{statusText}</span>
        <span className="who">for {ticket.assigned_to}</span>
      </div>
      {children && <div className="card-actions">{children}</div>}
    </article>
  );
};

export default TicketCard;