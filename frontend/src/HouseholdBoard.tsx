import React from 'react';

export default function HouseholdBoard({ board }: { board: { todo: Array<{ id: number; title: string; assigned_to: string }>; in_progress: Array<{ id: number; title: string; assigned_to: string }>; completed: Array<{ id: number; title: string; assigned_to: string }> } }) {
  return (
    <section>
      <h2>Household board</h2>
      <div>
        <h3>To Do</h3>
        {board.todo.map((ticket) => (
          <div key={ticket.id}>
            <div>{ticket.title}</div>
            <div data-assigned={ticket.assigned_to}>{ticket.assigned_to === 'her' ? 'for her' : 'for him'}</div>
          </div>
        ))}
      </div>
      <div>
        <h3>In Progress</h3>
        {board.in_progress.map((ticket) => (
          <div key={ticket.id}>
            <div>{ticket.title}</div>
            <div data-assigned={ticket.assigned_to}>{ticket.assigned_to === 'her' ? 'for her' : 'for him'}</div>
          </div>
        ))}
      </div>
      <div>
        <h3>Completed</h3>
        {board.completed.map((ticket) => (
          <div key={ticket.id}>
            <div>{ticket.title}</div>
            <div data-assigned={ticket.assigned_to}>{ticket.assigned_to === 'her' ? 'for her' : 'for him'}</div>
          </div>
        ))}
      </div>
    </section>
  );
}