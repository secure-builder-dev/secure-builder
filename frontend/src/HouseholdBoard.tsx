import React from "react";
import { Board } from "./types";
import TicketCard from "./TicketCard";

interface HouseholdBoardProps {
  board: Board;
}

const HouseholdBoard: React.FC<HouseholdBoardProps> = ({ board }) => {
  const columns: { name: string; tickets: typeof board.todo }[] = [
    { name: "To Do", tickets: board.todo },
    { name: "In Progress", tickets: board.in_progress },
    { name: "Completed", tickets: board.completed },
  ];

  return (
    <section className="panel" aria-label="Household board">
      <h2>Household board</h2>
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
                <TicketCard key={ticket.id} ticket={ticket} />
              ))
            )}
          </section>
        ))}
      </div>
    </section>
  );
};

export default HouseholdBoard;
