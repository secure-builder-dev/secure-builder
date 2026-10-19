import React, { useState } from "react";

type Ticket = {
  details: string;
  filed_by: "her" | "him";
  assigned_to: "her" | "him";
  created_at: string;
};

interface HoverCardProps {
  ticket: Ticket;
  children: React.ReactNode;
}

const HoverCard: React.FC<HoverCardProps> = ({ ticket, children }) => {
  const [visible, setVisible] = useState(false);

  const show = () => setVisible(true);
  const hide = () => setVisible(false);

  return (
    <span
      className="hover-target"
      tabIndex={0}
      onMouseEnter={show}
      onMouseLeave={hide}
      onFocus={show}
      onBlur={hide}
    >
      {children}
      {visible && (
        <div role="tooltip" className="hover-card">
          <p>{ticket.details.trim() ? ticket.details : "No details"}</p>
          <p>{`Filed by ${ticket.filed_by}`}</p>
          <p>{`Assigned to ${ticket.assigned_to}`}</p>
          <p>{`Created ${ticket.created_at.slice(0, 10)}`}</p>
        </div>
      )}
    </span>
  );
};

export default HoverCard;
