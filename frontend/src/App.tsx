import React, { useState, useEffect } from 'react';
import { fetchDashboard, fetchFiled, createTicket, updateTicketStatus, fetchBoard, fetchMe } from './api';
import './styles.css';
import HouseholdBoard from './HouseholdBoard';
import Menu from './Menu';
import Directions from './Directions';
import HoverCard from './HoverCard';


const App: React.FC = () => {
  const [token, setToken] = useState('');
  const [dashboard, setDashboard] = useState<{ todo: any[], in_progress: any[], completed: any[] }>({ todo: [], in_progress: [], completed: [] });
  const [filedTickets, setFiledTickets] = useState([]);
  const [error, setError] = useState('');
  const [householdBoard, setHouseholdBoard] = useState(null);
  const [showDirections, setShowDirections] = useState(false);
  const [user, setUser] = useState<string | null>(null);
  const [menu, setMenu] = useState('');

  const loadData = async () => {
    if (!token) return;
    setError('');
    try {
      const dashboardData = await fetchDashboard(token);
      setDashboard(dashboardData);
      const filedData = await fetchFiled(token);
      setFiledTickets(filedData.tickets);
      const boardData = await fetchBoard(token);
      setHouseholdBoard(boardData);
      const userData = await fetchMe(token);
      setUser(userData.user);
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
      <div className='topbar'>
        <Menu onDirections={() => setShowDirections(true)} />
        <input type='hidden' id='menu' value={menu} />
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

      {user && <p>Signed in as {user}</p>}
      {householdBoard && <HouseholdBoard board={householdBoard} />}
      {showDirections && <Directions onClose={() => setShowDirections(false)} />}
      <div>
        <h2>New ticket{user === 'her' ? ' for him' : user === 'him' ? ' for her' : ''}</h2>
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
      <div className='board'>
        <div className='column'>
          <h2>To Do</h2>
          {dashboard.todo.map((ticket) => (
            <div key={ticket.id} className={`card ${ticket.group === 0 ? 'urgent' : ''}`}>
              <HoverCard content={<div>
                        <p>{ticket.details}</p>
                        <p>Filed by {ticket.filed_by}</p>
                      </div>}>
                      <h3>{ticket.title}</h3>
                    </HoverCard>
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
        <div className='column'>
          <h2>In Progress</h2>
          {dashboard.in_progress.map((ticket) => (
            <div key={ticket.id} className={`card ${ticket.group === 0 ? 'urgent' : ''}`}>
              <HoverCard content={<div>
                        <p>{ticket.details}</p>
                        <p>Assigned to {ticket.assigned_to}</p>
                      </div>}>
                      <h3>{ticket.title}</h3>
                    </HoverCard>
                    <p>Priority: {ticket.priority}</p>
                    <p>Due: {ticket.due}</p>
                    <button onClick={() => handleStatusChange(ticket.id, 'done')}>Done</button>
            </div>
          ))}
        </div>
        <div className='column'>
          <h2>Completed</h2>
          {dashboard.completed.map((ticket) => (
            <div key={ticket.id} className='card'>
              <HoverCard content={<div>
                        <p>{ticket.details}</p>
                        <p>Created {ticket.created_at}</p>
                      </div>}>
                      <h3>{ticket.title}</h3>
                    </HoverCard>
                    <p>Priority: {ticket.priority}</p>
                    <p>Due: {ticket.due}</p>
            </div>
          ))}
        </div>
      </div>
      <div>
        <h2>Tickets I filed</h2>
        {filedTickets.map((ticket) => (
          <div key={ticket.id}>
            <h3>{ticket.title}</h3>
            <p>Priority: {ticket.priority}</p>
            <p>Due: {ticket.due}</p>
            {ticket.status === 'done' && (
              <>
                <button onClick={() => handleStatusChange(ticket.id, 'closed')}>Close</button>
                <button onClick={() => handleStatusChange(ticket.id, 'open')}>Reopen</button>
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default App;
