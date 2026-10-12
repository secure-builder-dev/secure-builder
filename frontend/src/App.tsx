import React, { useState } from 'react';
import { fetchDashboard, fetchFiled, createTicket, changeStatus } from './api';
import TicketCard from './TicketCard';
import './styles.css';

const App = () => {
  const [token, setToken] = useState('');
  const [dashboard, setDashboard] = useState<{ todo: any[]; in_progress: any[]; completed: any[] } | null>(null);
  const [filedTickets, setFiledTickets] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    title: '',
    details: '',
    priority: 'normal' as 'low' | 'normal' | 'urgent',
    due: ''
  });

  const handleLoad = async () => {
    try {
      const dash = await fetchDashboard(token);
      const filed = await fetchFiled(token);
      setDashboard(dash);
      setFiledTickets(filed.tickets);
      setError(null);
    } catch (err) {
      if (err instanceof Error && err.message === '401') {
        setError('Wrong token');
      } else {
        setError('Something went wrong');
      }
      setDashboard(null);
      setFiledTickets([]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createTicket(token, {
        title: formData.title,
        details: formData.details,
        priority: formData.priority,
        due: formData.due || null
      });
      setFormData({ title: '', details: '', priority: 'normal', due: '' });
      await handleLoad();
    } catch (err) {
      if (err instanceof Error && err.message === '401') {
        setError('Wrong token');
      } else {
        setError('Something went wrong');
      }
    }
  };

  const handleStatusChange = async (id: number, status: string) => {
    try {
      await changeStatus(token, id, status);
      await handleLoad();
    } catch (err) {
      if (err instanceof Error && err.message === '401') {
        setError('Wrong token');
      } else {
        setError('Something went wrong');
      }
    }
  };

  return (
    <div className="app">
      <header className="topbar">
        <h1 className="brand">~/honey-do</h1>
        <div className="token-form">
          <label htmlFor="token-input">Token</label>
          <input
            id="token-input"
            type="password"
            value={token}
            onChange={(e) => setToken(e.target.value)}
          />
          <button onClick={handleLoad}>Load</button>
        </div>
      </header>
      <main className="content">
        {error && <p role="alert" className="error">{error}</p>}
        <section className="panel new-ticket" aria-label="New ticket">
          <h2>New ticket</h2>
          <form onSubmit={handleSubmit}>
            <label htmlFor="title-input">Title</label>
            <input
              id="title-input"
              type="text"
              value={formData.title}
              onChange={(e) => setFormData({...formData, title: e.target.value})}
            />
            <label htmlFor="details-input">Details</label>
            <textarea
              id="details-input"
              value={formData.details}
              onChange={(e) => setFormData({...formData, details: e.target.value})}
            />
            <label htmlFor="priority-input">Priority</label>
            <select
              id="priority-input"
              value={formData.priority}
              onChange={(e) => setFormData({...formData, priority: e.target.value as 'low' | 'normal' | 'urgent'})}
            >
              <option value="low">low</option>
              <option value="normal">normal</option>
              <option value="urgent">urgent</option>
            </select>
            <label htmlFor="due-input">Due</label>
            <input
              id="due-input"
              type="date"
              value={formData.due}
              onChange={(e) => setFormData({...formData, due: e.target.value})}
            />
            <button type="submit">File ticket</button>
          </form>
        </section>
        {dashboard && (
          <section className="panel" aria-label="My board">
            <h2>My board</h2>
            <div className="board">
              <section className="column" aria-label="To Do">
                <h3 className="column-title">
                  To Do <span className="count">{dashboard.todo.length}</span>
                </h3>
                {dashboard.todo.length > 0 ? (
                  dashboard.todo.map((ticket) => (
                    <TicketCard key={ticket.id} ticket={ticket}>
                      {ticket.status === 'open' && <button onClick={() => handleStatusChange(ticket.id, 'acknowledged')}>Acknowledge</button>}
                      {ticket.status === 'acknowledged' && <button onClick={() => handleStatusChange(ticket.id, 'in_progress')}>Start</button>}
                    </TicketCard>
                  ))
                ) : (
                  <p className="empty">Nothing here</p>
                )}
              </section>
              <section className="column" aria-label="In Progress">
                <h3 className="column-title">
                  In Progress <span className="count">{dashboard.in_progress.length}</span>
                </h3>
                {dashboard.in_progress.length > 0 ? (
                  dashboard.in_progress.map((ticket) => (
                    <TicketCard key={ticket.id} ticket={ticket}>
                      {ticket.status === 'in_progress' && <button onClick={() => handleStatusChange(ticket.id, 'done')}>Done</button>}
                    </TicketCard>
                  ))
                ) : (
                  <p className="empty">Nothing here</p>
                )}
              </section>
              <section className="column" aria-label="Completed">
                <h3 className="column-title">
                  Completed <span className="count">{dashboard.completed.length}</span>
                </h3>
                {dashboard.completed.length > 0 ? (
                  dashboard.completed.map((ticket) => (
                    <TicketCard key={ticket.id} ticket={ticket} />
                  ))
                ) : (
                  <p className="empty">Nothing here</p>
                )}
              </section>
            </div>
          </section>
        )}
        {dashboard && (
          <section className="panel" aria-label="Tickets I filed">
            <h2>Tickets I filed</h2>
            <div className="card-list">
              {filedTickets.map((ticket) => (
                <TicketCard key={ticket.id} ticket={ticket}>
                  {ticket.status === 'done' && (
                    <>
                      <button onClick={() => handleStatusChange(ticket.id, 'closed')}>Close</button>
                      <button onClick={() => handleStatusChange(ticket.id, 'open')}>Reopen</button>
                    </>
                  )}
                </TicketCard>
              ))}
            </div>
          </section>
        )}
      </main>
    </div>
  );
};

export default App;