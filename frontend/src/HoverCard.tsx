import React, { useState, useRef } from "react";
import type { Ticket } from "./types";

interface HoverCardProps {
  ticket: Ticket;
  children: React.ReactNode;
}

export default function HoverCard({ ticket, children }: HoverCardProps) {
  const [showTooltip, setShowTooltip] = useState(false);
  const spanRef = useRef<HTMLSpanElement>(null);

  const handleMouseEnter = () => setShowTooltip(true);
  const handleMouseLeave = () => setShowTooltip(false);
  const handleFocus = () => setShowTooltip(true);
  const handleBlur = () => setShowTooltip(false);

  const detailsText = ticket.details.trim() || "No details";
  const createdText = ticket.created_at.slice(0, 10);

  return (
    <span
      ref={spanRef}
      className="hover-target"
      tabIndex={0}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onFocus={handleFocus}
      onBlur={handleBlur}
    >
      {children}
      {showTooltip && (
        <div role="tooltip" className="hover-card">
          <p>{detailsText}</p>
          <p>Filed by {ticket.filed_by}</p>
          <p>Assigned to {ticket.assigned_to}</p>
          <p>Created {createdText}</p>
        </div>
      )}
    </span>
  );
}