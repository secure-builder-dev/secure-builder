import React, { ReactNode } from "react";
import type { Board, Ticket } from "./types";
import TicketCard from "./TicketCard";

interface HouseholdBoardProps {
  board: Board;
  onOpen?: (ticket: Ticket) => void;
  children?: ReactNode;
}

/**
 * HouseholdBoard renders the shared board for both users.
 * It displays three columns (To Do, In Progress, Completed) with ticket counts,
 * ticket cards, and an empty message when a column has no tickets.
 */
export default function HouseholdBoard({ board, onOpen, children }: HouseholdBoardProps) {
  const columns = [
    { name: "To Do", tickets: board.todo },
    { name: "In Progress", tickets: board.in_progress },
    { name: "Completed", tickets: board.completed },
  ];

  return (
    <section className="panel" aria-label="Household board">
      <h2>Household board</h2>
      {children}
      <div className="board">
        {columns.map((col) => (
          <section
            key={col.name}
            className="column"
            role="region"
            aria-label={col.name}
          >
            <h3 className="column-title">
              {col.name} <span className="count">{col.tickets.length}</span>
            </h3>
            {col.tickets.length > 0 ? (
              col.tickets.map((ticket) => (
                <TicketCard
                  key={ticket.id}
                  ticket={ticket}
                  {...(onOpen ? { onOpen } : {})}
                />
              ))
            ) : (
              <p className="empty">Nothing here</p>
            )}
          </section>
        ))}
      </div>
    </section>
  );
}
