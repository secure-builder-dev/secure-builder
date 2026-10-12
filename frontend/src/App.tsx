import React, { useState } from 'react';
import { fetchDashboard, fetchFiled } from './api';
import TicketCard from './TicketCard';
import './styles.css';

const App = () => {
  const [token, setToken] = useState('');
  const [dashboard, setDashboard] = useState<{ todo: any[]; in_progress: any[]; completed: any[] } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      const dash = await fetchDashboard(token);
      setDashboard(dash);
      setError(null);
    } catch (err) {
      if (err instanceof Error && err.message === '401') {
        setError('Wrong token');
      } else {
        setError('Something went wrong');
      }
      setDashboard(null);
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
          <button onClick={loadData}>Load</button>
        </div>
      </header>
      <main className="content">
        {error && <p role="alert" className="error">{error}</p>}
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
                    <TicketCard key={ticket.id} ticket={ticket} />
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
                    <TicketCard key={ticket.id} ticket={ticket} />
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
      </main>
    </div>
  );
};

export default App;