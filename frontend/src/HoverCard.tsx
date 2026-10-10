import React, { useState } from 'react';

interface Ticket {
  details: string;
  filed_by: string;
  assigned_to: string;
  created_at: string;
}

interface HoverCardProps {
  ticket: Ticket;
  children: React.ReactNode;
}

const HoverCard: React.FC<HoverCardProps> = ({ ticket, children }) => {
  const [isHovered, setIsHovered] = useState(false);

  const handleMouseEnter = () => setIsHovered(true);
  const handleMouseLeave = () => setIsHovered(false);
  const handleFocus = () => setIsHovered(true);
  const handleBlur = () => setIsHovered(false);

  return (
    <span
      className='hover-target'
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onFocus={handleFocus}
      onBlur={handleBlur}
    >
      {children}
      {isHovered && (
        <span
          role='tooltip'
          className='hover-card'
        >
          <div>{ticket.details || 'No details'}</div>
          <div>Filed by {ticket.filed_by}</div>
          <div>Assigned to {ticket.assigned_to}</div>
          <div>Created {ticket.created_at.slice(0, 10)}</div>
        </span>
      )}
    </span>
  );
}

export default HoverCard;