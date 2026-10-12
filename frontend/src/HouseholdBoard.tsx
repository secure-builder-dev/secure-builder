import React from 'react';
import type { Board } from './types';
import TicketCard from './TicketCard';

const HouseholdBoard = ({ board }: { board: Board }) => {
  return (
    <section className="panel" aria-label="Household board">
      <h2>Household board</h2>
      <div className="board">
        <section className="column" aria-label="To Do">
          <h3 className="column-title">To Do <span className="count">{board.todo.length}</span></h3>
          {board.todo.length > 0 ? (
            board.todo.map((ticket) => (
              <TicketCard key={ticket.id} ticket={ticket} />
            ))
          ) : (
            <p className="empty">Nothing here</p>
          )}
        </section>
        <section className="column" aria-label="In Progress">
          <h3 className="column-title">In Progress <span className="count">{board.in_progress.length}</span></h3>
          {board.in_progress.length > 0 ? (
            board.in_progress.map((ticket) => (
              <TicketCard key={ticket.id} ticket={ticket} />
            ))
          ) : (
            <p className="empty">Nothing here</p>
          )}
        </section>
        <section className="column" aria-label="Completed">
          <h3 className="column-title">Completed <span className="count">{board.completed.length}</span></h3>
          {board.completed.length > 0 ? (
            board.completed.map((ticket) => (
              <TicketCard key={ticket.id} ticket={ticket} />
            ))
          ) : (
            <p className="empty">Nothing here</p>
          )}
        </section>
      </div>
    </section>
  );
};

export default HouseholdBoard;
