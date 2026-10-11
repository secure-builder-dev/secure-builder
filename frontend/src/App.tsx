import { useState } from 'react';
import './styles.css';
import HoverCard from './HoverCard';

interface Ticket {
  id: number;
  title: string;
  details: string;
  priority: 'low' | 'normal' | 'urgent';
  due: string | null;
  status: string;
  filed_by: string;
  assigned_to: string;
  created_at: string;
  updated_at: string;
  group?: number;
}

interface DashboardData {
  todo: Ticket[];
  in_progress: Ticket[];
  completed: Ticket[];
}

interface FiledData {
  tickets: Ticket[];
}

function App() {
  const [token, setToken] = useState('');
  const [error, setError] = useState('');
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [filedData, setFiledData] = useState<FiledData | null>(null);
  const [user, setUser] = useState<string | null>(null);

  const handleLoad = async () => {
    try {
      const dashResponse = await fetch('/api/dashboard', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!dashResponse.ok) {
        throw new Error(dashResponse.status.toString());
      }
      
      const filedResponse = await fetch('/api/filed', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!filedResponse.ok) {
        throw new Error(filedResponse.status.toString());
      }
      
      const meResponse = await fetch('/api/me', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!meResponse.ok) {
        setUser(null);
      } else {
        const me = await meResponse.json();
        setUser(me.user);
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
        throw new Error(response.status.toString());
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
        throw new Error(response.status.toString());
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
      <div className="topbar">
        <h1 className="brand">~/honey-do</h1>
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
        <h2>{user ? `New ticket for ${user === 'her' ? 'him' : 'her'}` : 'New Ticket'}</h2>
        {user && <div>Signed in as {user}</div>}
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
        <main>
          <div className="board">
            <div className="column">
              <h3>To Do</h3>
              {dashboardData.todo.map((ticket: Ticket) => (
                <div key={ticket.id} className={"card " + (ticket.group === 0 ? 'urgent' : '')}>
                  <h4><HoverCard ticket={ticket}>{ticket.title}</HoverCard></h4>
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
              {dashboardData.in_progress.map((ticket: Ticket) => (
                <div key={ticket.id} className={"card " + (ticket.group === 0 ? 'urgent' : '')}>
                  <h4><HoverCard ticket={ticket}>{ticket.title}</HoverCard></h4>
                  <p>Priority: {ticket.priority}</p>
                  <p>Due: {ticket.due || 'No due date'}</p>
                  <button onClick={() => handleStatusChange(ticket.id, 'done')}>Done</button>
                </div>
              ))}
            </div>
            
            <div className="column">
              <h3>Completed</h3>
              {dashboardData.completed.map((ticket: Ticket) => (
                <div key={ticket.id} className="card">
                  <h4><HoverCard ticket={ticket}>{ticket.title}</HoverCard></h4>
                  <p>Priority: {ticket.priority}</p>
                  <p>Due: {ticket.due || 'No due date'}</p>
                </div>
              ))}
            </div>
          </div>
        </main>
      )}

      {filedData?.tickets && (
        <div className="filed-tickets">
          <h2>Tickets I Filed</h2>
          {filedData.tickets.map((ticket: Ticket) => (
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