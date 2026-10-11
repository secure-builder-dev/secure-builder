import React from 'react';

interface Ticket {
  id: number;
  title: string;
  assigned_to: 'her' | 'him';
}

interface BoardData {
  todo: Ticket[];
  in_progress: Ticket[];
  completed: Ticket[];
}

export default function HouseholdBoard({ board }: { board: BoardData }) {
  const renderTickets = (tickets: Ticket[], columnKey: string) => (
    <div role="gridcell">
      <h3>{columnKey === 'todo' ? 'To Do' : columnKey === 'in_progress' ? 'In Progress' : 'Completed'}</h3>
      {tickets.map((ticket) => (
        <div key={ticket.id} className="card">
          <p>{ticket.title}</p>
          <p>for {ticket.assigned_to}</p>
        </div>
      ))}
    </div>
  );

  return (
    <section>
      <h2>Household board</h2>
      <div role="grid">
        {renderTickets(board.todo, 'todo')}
        {renderTickets(board.in_progress, 'in_progress')}
        {renderTickets(board.completed, 'completed')}
      </div>
    </section>
  );
}
