import { useState, useEffect } from 'react';
import { fetchDashboard, fetchFiled, createTicket, updateStatus } from './api';
import './styles.css';

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

interface Dashboard {
  todo: Ticket[];
  in_progress: Ticket[];
  completed: Ticket[];
}

const App = () => {
  const [token, setToken] = useState('');
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [filedTickets, setFiledTickets] = useState<Ticket[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [newTicket, setNewTicket] = useState({
    title: '',
    details: '',
    priority: 'normal' as 'low' | 'normal' | 'urgent',
    due: ''
  });

  const handleLoad = async () => {
    if (!token) {
      setError('Token is required');
      return;
    }
    try {
      const dash = await fetchDashboard(token);
      const filed = await fetchFiled(token);
      setDashboard(dash);
      setFiledTickets(filed.tickets);
      setError(null);
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      }
    }
  };

  const handleCreateTicket = async () => {
    try {
      await createTicket(token, newTicket);
      await handleLoad();
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      }
    }
  };

  const handleStatusUpdate = async (ticketId: number, newStatus: string) => {
    try {
      await updateStatus(token, ticketId, newStatus);
      await handleLoad();
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      }
    }
  };

  return (
    <div>
      <div className="topbar">
        <h1 className="brand">~/honey-do</h1>
        <label htmlFor="token">Token</label>
        <input
          id="token"
          type="password"
          value={token}
          onChange={(e) => setToken(e.target.value)}
        />
        <button id="load-button" onClick={handleLoad}>Load</button>
      </div>
      
      {error && <div>{error}</div>}
      
      <div>
        <h2>New ticket</h2>
        <form onSubmit={(e) => {
          e.preventDefault();
          handleCreateTicket();
        }}>
          <div>
            <label htmlFor="title">Title</label>
            <input
              id="title"
              value={newTicket.title}
              onChange={(e) => setNewTicket({...newTicket, title: e.target.value})}
            />
          </div>
          <div>
            <label htmlFor="details">Details</label>
            <textarea
              id="details"
              value={newTicket.details}
              onChange={(e) => setNewTicket({...newTicket, details: e.target.value})}
            />
          </div>
          <div>
            <label htmlFor="priority">Priority</label>
            <select
              id="priority"
              value={newTicket.priority}
              onChange={(e) => setNewTicket({...newTicket, priority: e.target.value as 'low' | 'normal' | 'urgent'})}
            >
              <option value="low">low</option>
              <option value="normal">normal</option>
              <option value="urgent">urgent</option>
            </select>
          </div>
          <div>
            <label htmlFor="due">Due</label>
            <input
              id="due"
              type="date"
              value={newTicket.due}
              onChange={(e) => setNewTicket({...newTicket, due: e.target.value})}
            />
          </div>
          <button type="submit" id="file-ticket-button">File ticket</button>
        </form>
      </div>
      
      {dashboard && (
        <div className="board">
          <div className="column">
            <h3>Board</h3>
            <h3>To Do</h3>
            {dashboard.todo.map((ticket) => (
              <div key={ticket.id} className={`card ${ticket.group === 0 ? 'urgent' : ''}`}>
                <h4>{ticket.title}</h4>
                <p>Priority: {ticket.priority}</p>
                <p>Due: {ticket.due ? ticket.due : 'No due date'}</p>
                {ticket.status === 'open' && (
                  <button onClick={() => handleStatusUpdate(ticket.id, 'acknowledged')}>Acknowledge</button>
                )}
                {ticket.status === 'acknowledged' && (
                  <button onClick={() => handleStatusUpdate(ticket.id, 'in_progress')}>Start</button>
                )}
              </div>
            ))}
          </div>
          <div className="column">
            <h3>In Progress</h3>
            {dashboard.in_progress.map((ticket) => (
              <div key={ticket.id} className={`card ${ticket.group === 0 ? 'urgent' : ''}`}>
                <h4>{ticket.title}</h4>
                <p>Priority: {ticket.priority}</p>
                <p>Due: {ticket.due ? ticket.due : 'No due date'}</p>
                <button onClick={() => handleStatusUpdate(ticket.id, 'done')}>Done</button>
              </div>
            ))}
          </div>
          <div className="column">
            <h3>Completed</h3>
            {dashboard.completed.map((ticket) => (
              <div key={ticket.id} className={`card ${ticket.group === 0 ? 'urgent' : ''}`}>
                <h4>{ticket.title}</h4>
                <p>Priority: {ticket.priority}</p>
                <p>Due: {ticket.due ? ticket.due : 'No due date'}</p>
              </div>
            ))}
          </div>
        </div>
      )}
      
      <div>
        <h2>Tickets I filed</h2>
        {filedTickets.map((ticket) => (
          <div key={ticket.id} className="card">
            <h4>{ticket.title}</h4>
            <p>Priority: {ticket.priority}</p>
            <p>Due: {ticket.due ? new Date(ticket.due).toLocaleDateString() : 'No due date'}</p>
            {ticket.status === 'done' && (
              <>
                <button onClick={() => handleStatusUpdate(ticket.id, 'closed')}>Close</button>
                <button onClick={() => handleStatusUpdate(ticket.id, 'open')}>Reopen</button>
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  );


};

export default App;