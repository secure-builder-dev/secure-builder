import { useState, ReactNode, FocusEvent, MouseEvent } from "react";
import { Ticket } from "./types";

interface HoverCardProps {
  ticket: Ticket;
  children: ReactNode;
}

export default function HoverCard({ ticket, children }: HoverCardProps) {
  const [visible, setVisible] = useState(false);

  const show = () => setVisible(true);
  const hide = () => setVisible(false);

  const handleMouseEnter = (e: MouseEvent) => show();
  const handleMouseLeave = (e: MouseEvent) => hide();
  const handleFocus = (e: FocusEvent) => show();
  const handleBlur = (e: FocusEvent) => hide();

  const detailsText = ticket.details.trim() ? ticket.details : "No details";
  const createdDate = ticket.created_at.slice(0, 10);

  return (
    <span
      className="hover-target"
      tabIndex={0}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onFocus={handleFocus}
      onBlur={handleBlur}
    >
      {children}
      {visible && (
        <div role="tooltip" className="hover-card">
          <p>{detailsText}</p>
          <p>{`Filed by ${ticket.filed_by}`}</p>
          <p>{`Assigned to ${ticket.assigned_to}`}</p>
          <p>{`Created ${createdDate}`}</p>
        </div>
      )}
    </span>
  );
}
