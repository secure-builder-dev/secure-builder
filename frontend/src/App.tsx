import React, { useState, useEffect } from 'react';
import { fetchDashboard, fetchFiled, createTicket, updateTicketStatus } from './api';

const App: React.FC = () => {
  const [token, setToken] = useState('');
  const [dashboard, setDashboard] = useState({ todo: [], in_progress: [], completed: [] });
  const [filedTickets, setFiledTickets] = useState([]);
  const [error, setError] = useState('');

  const loadData = async () => {
    if (!token) return;
    setError('');
    try {
      const dashboardData = await fetchDashboard(token);
      setDashboard(dashboardData);
      const filedData = await fetchFiled(token);
      setFiledTickets(filedData.tickets);
    } catch (err) {
      if (err.message === '401') {
        setError('Wrong token');
      } else {
        setError('Something went wrong');
      }
    }
  };

  const handleCreateTicket = async (title: string, details: string, priority: string, due: string) => {
    await createTicket(token, title, details, priority, due);
    loadData();
  };

  const handleStatusChange = async (ticketId: number, status: string) => {
    await updateTicketStatus(token, ticketId, status);
    loadData();
  };

  return (
    <div>
      <div>
        <label htmlFor='token'>Token</label>
        <input
          id='token'
          type='password'
          value={token}
          onChange={(e) => setToken(e.target.value)}
        />
        <button onClick={loadData}>Load</button>
      </div>
      {error && <p>{error}</p>}
      <div>
        <h2>New ticket</h2>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            const formData = new FormData(e.target as HTMLFormElement);
            const title = formData.get('title') as string;
            const details = formData.get('details') as string;
            const priority = formData.get('priority') as string;
            const due = formData.get('due') as string;
            handleCreateTicket(title, details, priority, due);
          }}
        >
          <label htmlFor='title'>Title</label>
          <input id='title' name='title' required />
          <label htmlFor='details'>Details</label>
          <input id='details' name='details' />
          <label htmlFor='priority'>Priority</label>
          <select id='priority' name='priority'>
            <option value='low'>low</option>
            <option value='normal'>normal</option>
            <option value='urgent'>urgent</option>
          </select>
          <label htmlFor='due'>Due</label>
          <input id='due' name='due' type='date' />
          <button type='submit'>File ticket</button>
        </form>
      </div>
      <div>
        <h2>To Do</h2>
        {dashboard.todo.map((ticket) => (
          <div key={ticket.id} className={ticket.group === 0 ? 'urgent' : ''}>
            <h3>{ticket.title}</h3>
            <p>Priority: {ticket.priority}</p>
            <p>Due: {ticket.due}</p>
            {ticket.status === 'open' && (
              <button onClick={() => handleStatusChange(ticket.id, 'acknowledged')}>Acknowledge</button>
            )}
            {ticket.status === 'acknowledged' && (
              <button onClick={() => handleStatusChange(ticket.id, 'in_progress')}>Start</button>
            )}
          </div>
        ))}
      </div>
      <div>
        <h2>In Progress</h2>
        {dashboard.in_progress.map((ticket) => (
          <div key={ticket.id} className={ticket.group === 0 ? 'urgent' : ''}>
            <h3>{ticket.title}</h3>
            <p>Priority: {ticket.priority}</p>
            <p>Due: {ticket.due}</p>
            <button onClick={() => handleStatusChange(ticket.id, 'done')}>Done</button>
          </div>
        ))}
      </div>
      <div>
        <h2>Completed</h2>
        {dashboard.completed.map((ticket) => (
          <div key={ticket.id}>
            <h3>{ticket.title}</h3>
            <p>Priority: {ticket.priority}</p>
            <p>Due: {ticket.due}</p>
          </div>
        ))}
      </div>
      <div>
        <h2>Tickets I filed</h2>
        {filedTickets.map((ticket) => (
          <div key={ticket.id}>
            <h3>{ticket.title}</h3>
            <p>Priority: {ticket.priority}</p>
            <p>Due: {ticket.due}</p>
            {ticket.status === 'done' && (
              <button onClick={() => handleStatusChange(ticket.id, 'closed')}>Close</button>
              <button onClick={() => handleStatusChange(ticket.id, 'open')}>Reopen</button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default App;
