import React, { ReactNode } from "react";
import { Board, Ticket } from "./types";
import TicketCard from "./TicketCard";

interface HouseholdBoardProps {
  board: Board;
  onOpen?: (ticket: Ticket) => void;
  children?: ReactNode;
}

const HouseholdBoard: React.FC<HouseholdBoardProps> = ({ board, onOpen, children }) => {
  const columns: { name: string; tickets: typeof board.todo }[] = [
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
          <section key={col.name} className="column" aria-label={col.name}>
            <h3 className="column-title">
              {col.name} <span className="count">{col.tickets.length}</span>
            </h3>
            {col.tickets.length === 0 ? (
              <p className="empty">Nothing here</p>
            ) : (
              col.tickets.map((ticket) => (
                <TicketCard key={ticket.id} ticket={ticket} onOpen={onOpen} />
              ))
            )}
          </section>
        ))}
      </div>
    </section>
  );
};

export default HouseholdBoard;
