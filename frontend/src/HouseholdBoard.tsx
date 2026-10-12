import React from "react";
import type { Board, Ticket } from "./types";
import TicketCard from "./TicketCard";

interface HouseholdBoardProps {
  board: Board;
}

function Column({ name, tickets }: { name: string; tickets: Ticket[] }) {
  return (
    <section className="column" aria-label={name}>
      <h3 className="column-title">
        {name} <span className="count">{tickets.length}</span>
      </h3>
      {tickets.length === 0 ? (
        <p className="empty">Nothing here</p>
      ) : (
        tickets.map((t) => <TicketCard key={t.id} ticket={t} />)
      )}
    </section>
  );
}

export default function HouseholdBoard({ board }: HouseholdBoardProps) {
  return (
    <section className="panel" aria-label="Household board">
      <h2>Household board</h2>
      <div className="board">
        <Column name="To Do" tickets={board.todo} />
        <Column name="In Progress" tickets={board.in_progress} />
        <Column name="Completed" tickets={board.completed} />
      </div>
    </section>
  );
}
