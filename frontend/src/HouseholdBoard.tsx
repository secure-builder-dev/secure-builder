import React from 'react';

export default function HouseholdBoard({ board }: { board: { todo: Array<{ id: number; title: string; assigned_to: string }>; in_progress: Array<{ id: number; title: string; assigned_to: string }>; completed: Array<{ id: number; title: string; assigned_to: string }> } }) {
  return (
    <section aria-labelledby="household-board-heading">
      <h2 id="household-board-heading">Household board</h2>
      <div role="grid">
        <div role="gridcell">
          <h3>To Do</h3>
          {board.todo.map((ticket) => (
            <div key={ticket.id} role="row">
              <div>{ticket.title}</div>
              <div data-assigned-to>{ticket.assigned_to === 'him' ? 'for him' : 'for her'}</div>
            </div>
          ))}
        </div>
        <div role="gridcell">
          <h3>In Progress</h3>
          {board.in_progress.map((ticket) => (
            <div key={ticket.id} role="row">
              <div>{ticket.title}</div>
              <div data-assigned-to>{ticket.assigned_to === 'him' ? 'for him' : 'for her'}</div>
            </div>
          ))}
        </div>
        <div role="gridcell">
          <h3>Completed</h3>
          {board.completed.map((ticket) => (
            <div key={ticket.id} role="row">
              <div>{ticket.title}</div>
              <div data-assigned-to>{ticket.assigned_to === 'him' ? 'for him' : 'for her'}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
