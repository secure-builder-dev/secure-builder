import React from 'react';

export default function HouseholdBoard({ board }) {
  return (
    <section>
      <h2>Household board</h2>
      <div>
        <h3>To Do</h3>
        {board.todo && board.todo.map(ticket => (
          <div key={ticket.id}>
            <h4>{ticket.title}</h4>
            <p>{ticket.assigned_to === 'him' ? 'for him' : 'for her'}</p>
          </div>
        ))}
      </div>
      <div>
        <h3>In Progress</h3>
        {board.in_progress && board.in_progress.map(ticket => (
          <div key={ticket.id}>
            <h4>{ticket.title}</h4>
            <p>{ticket.assigned_to === 'him' ? 'for him' : 'for her'}</p>
          </div>
        ))}
      </div>
      <div>
        <h3>Completed</h3>
        {board.completed && board.completed.map(ticket => (
          <div key={ticket.id}>
            <h4>{ticket.title}</h4>
            <p>{ticket.assigned_to === 'him' ? 'for him' : 'for her'}</p>
          </div>
        ))}
      </div>
    </section>
  );
}