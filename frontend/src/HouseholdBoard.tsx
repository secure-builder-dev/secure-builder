import React from 'react';

type Ticket = {
  id: number;
  title: string;
  assigned_to: string;
};

type Board = {
  todo: Ticket[];
  in_progress: Ticket[];
  completed: Ticket[];
};

export default function HouseholdBoard({ board }: { board: Board }) {
  return (
    <div>
      <h2>Household board</h2>
      <div role="grid">
        <div role="gridcell">
          <h3>To Do</h3>
          {board.todo.map((ticket) => (
            <div key={ticket.id}>
              {ticket.title}
              <br />
              {ticket.assigned_to === 'him' ? 'for him' : 'for her'}
            </div>
          ))}
        </div>
        <div role="gridcell">
          <h3>In Progress</h3>
          {board.in_progress.map((ticket) => (
            <div key={ticket.id}>
              {ticket.title}
              <br />
              {ticket.assigned_to === 'him' ? 'for him' : 'for her'}
            </div>
          ))}
        </div>
        <div role="gridcell">
          <h3>Completed</h3>
          {board.completed.map((ticket) => (
            <div key={ticket.id}>
              {ticket.title}
              <br />
              {ticket.assigned_to === 'him' ? 'for him' : 'for her'}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
