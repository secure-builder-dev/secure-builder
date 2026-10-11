import { useState } from 'react';
import './App.css';

function App() {
  const [token, setToken] = useState('');
  const [error, setError] = useState('');
  const [dashboardData, setDashboardData] = useState(null);
  const [filedData, setFiledData] = useState(null);

  const handleLoad = async () => {
    try {
      const dashResponse = await fetch('/api/dashboard', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!dashResponse.ok) {
        throw new Error(dashResponse.status);
      }
      
      const filedResponse = await fetch('/api/filed', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!filedResponse.ok) {
        throw new Error(filedResponse.status);
      }
      
      const dash = await dashResponse.json();
      const filed = await filedResponse.json();
      
      setDashboardData(dash);
      setFiledData(filed);
    } catch (err: unknown) {
      if (err instanceof Error && err.message === '401') {
        setError('Wrong token');
      } else {
        setError('Something went wrong');
      }
    }
  };

  const handleCreateTicket = async (e: React.FormEvent) => {
    e.preventDefault();
    const form = e.target as HTMLFormElement;
    const formData = new FormData(form);
    const formJson = Object.fromEntries(formData.entries());
    
    try {
      const response = await fetch('/api/tickets', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(formJson)
      });
      
      if (!response.ok) {
        throw new Error(response.status);
      }
      
      await handleLoad();
    } catch (err: unknown) {
      if (err instanceof Error && err.message === '401') {
        setError('Wrong token');
      } else {
        setError('Something went wrong');
      }
    }
  };

  const handleStatusChange = async (ticketId: number, newStatus: string) => {
    try {
      const response = await fetch(`/api/tickets/${ticketId}/status`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ status: newStatus })
      });
      
      if (!response.ok) {
        throw new Error(response.status);
      }
      
      await handleLoad();
    } catch (err: unknown) {
      if (err instanceof Error && err.message === '401') {
        setError('Wrong token');
      } else {
        setError('Something went wrong');
      }
    }
  };

  return (
    <div className="app">
      <h1>Honey-Do Tickets</h1>
      
      <div className="token-section">
        <label htmlFor="token">Token</label>
        <input
          id="token"
          type="password"
          value={token}
          onChange={(e) => setToken(e.target.value)}
        />
        <button onClick={handleLoad}>Load</button>
      </div>
      
      {error && <div className="error">{error}</div>}

      <div className="new-ticket-form">
        <h2>New Ticket</h2>
        <form onSubmit={handleCreateTicket}>
          <label htmlFor="title">Title</label>
          <input id="title" name="title" required />
          
          <label htmlFor="details">Details</label>
          <textarea id="details" name="details" />
          
          <label htmlFor="priority">Priority</label>
          <select id="priority" name="priority">
            <option value="low">low</option>
            <option value="normal">normal</option>
            <option value="urgent">urgent</option>
          </select>
          
          <label htmlFor="due">Due</label>
          <input id="due" name="due" type="date" />
          
          <button type="submit">File Ticket</button>
        </form>
      </div>

      {dashboardData && (
        <div className="board">
          <div className="column">
            <h3>To Do</h3>
            {dashboardData.todo.map(ticket => (
              <div key={ticket.id} className={ticket.group === 0 ? 'urgent' : ''}>
                <h4>{ticket.title}</h4>
                <p>Priority: {ticket.priority}</p>
                <p>Due: {ticket.due || 'No due date'}</p>
                {ticket.status === 'open' && (
                  <button onClick={() => handleStatusChange(ticket.id, 'acknowledged')}>Acknowledge</button>
                )}
                {ticket.status === 'acknowledged' && (
                  <button onClick={() => handleStatusChange(ticket.id, 'in_progress')}>Start</button>
                )}
              </div>
            ))}
          </div>
          
          <div className="column">
            <h3>In Progress</h3>
            {dashboardData.in_progress.map(ticket => (
              <div key={ticket.id} className={ticket.group === 0 ? 'urgent' : ''}>
                <h4>{ticket.title}</h4>
                <p>Priority: {ticket.priority}</p>
                <p>Due: {ticket.due || 'No due date'}</p>
                <button onClick={() => handleStatusChange(ticket.id, 'done')}>Done</button>
              </div>
            ))}
          </div>
          
          <div className="column">
            <h3>Completed</h3>
            {dashboardData.completed.map(ticket => (
              <div key={ticket.id}>
                <h4>{ticket.title}</h4>
                <p>Priority: {ticket.priority}</p>
                <p>Due: {ticket.due || 'No due date'}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {filedData && (
        <div className="filed-tickets">
          <h2>Tickets I Filed</h2>
          {filedData.tickets.map(ticket => (
            <div key={ticket.id}>
              <h4>{ticket.title}</h4>
              <p>Status: {ticket.status}</p>
              {ticket.status === 'done' && (
                <>
                  <button onClick={() => handleStatusChange(ticket.id, 'closed')}>Close</button>
                  <button onClick={() => handleStatusChange(ticket.id, 'open')}>Reopen</button>
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default App;