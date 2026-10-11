import React from 'react';
import type { BoardData } from './api';

interface HouseholdBoardProps {
  board: BoardData;
}

export default function HouseholdBoard({ board }: HouseholdBoardProps) {
  const renderTicket = (ticket: NonNullable<BoardData['todo']>[number]) => (
    <article key={ticket.id} className={`card${ticket.priority === 'urgent' ? ' urgent' : ''}`}>
      <p>{ticket.title}</p>
      <span>{ticket.assigned_to}</span>
    </article>
  );

  const renderTickets = (tickets: NonNullable<BoardData['todo']>, columnLabel: string) => (
    <div key={columnLabel} className="column">
      <h3>{columnLabel}</h3>
      {tickets.map(renderTicket)}
    </div>
  );

  return (
    <section className="board">
      <h2>Household board</h2>
      {renderTickets(board.todo, 'To Do')}
      {renderTickets(board.in_progress, 'In Progress')}
      {renderTickets(board.completed, 'Completed')}
    </section>
  );
}
