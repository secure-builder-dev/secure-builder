import { useState, useEffect } from 'react';
import './styles.css';
import HoverCard from './HoverCard';
import Menu from './Menu';
import Directions from './Directions';
import HouseholdBoard from './HouseholdBoard';

const App = () => {
  const [token, setToken] = useState('');
  const [data, setData] = useState<{ dash: any; filed: any; me: any; board?: any } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [title, setTitle] = useState('');
  const [details, setDetails] = useState('');
  const [priority, setPriority] = useState('normal');
  const [due, setDue] = useState('');
  const [showDirections, setShowDirections] = useState(false);

  const loadData = async () => {
    try {
      const dashRes = await fetch('/api/dashboard', {
        headers: { Authorization: `Bearer ${token}` }
      });
      const filedRes = await fetch('/api/filed', {
        headers: { Authorization: `Bearer ${token}` }
      });
      const meRes = await fetch('/api/me', {
        headers: { Authorization: `Bearer ${token}` }
      });
      const boardRes = await fetch('/api/board', {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (!dashRes.ok || !filedRes.ok || !meRes.ok) {
        if (dashRes.status === 401 || filedRes.status === 401 || meRes.status === 401) {
          setError('Wrong token');
        } else {
          setError('Something went wrong');
        }
        return;
      }

      const dash = await dashRes.json();
      const filed = await filedRes.json();
      const me = await meRes.json();
      let board = { todo: [], in_progress: [], completed: [] };
      if (boardRes.ok) {
        board = await boardRes.json();
      }
      setData({ dash, filed, me, board });
      setError(null);
    } catch (err) {
      setError('Something went wrong');
    }
  };

  const createTicket = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch('/api/tickets', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ title, details, priority, due })
      });
      if (res.ok) {
        setTitle('');
        setDetails('');
        setPriority('normal');
        setDue('');
        await loadData();
      } else {
        setError('Something went wrong');
      }
    } catch (err) {
      setError('Something went wrong');
    }
  };

  const changeStatus = async (ticketId: number, newStatus: string) => {
    try {
      const res = await fetch(`/api/tickets/${ticketId}/status`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ status: newStatus })
      });
      if (res.ok) {
        await loadData();
      } else {
        setError('Something went wrong');
      }
    } catch (err) {
      setError('Something went wrong');
    }
  };

  return (
    <div>
      <div className="topbar">
        <h1 className="brand">~/honey-do</h1>
        <Menu onDirections={() => setShowDirections(true)} />
        <label>
          Token:
          <input
            type="password"
            value={token}
            onChange={(e) => setToken(e.target.value)}
          />
        </label>
        <button onClick={loadData}>Load</button>
      </div>
      {showDirections && <Directions onClose={() => setShowDirections(false)} />}
      {error && <div>{error}</div>}
      {data?.me && (
        <div>
          <p>Signed in as {data.me.user}</p>
          <p>New ticket for {data.me.user === 'her' ? 'him' : 'her'}</p>
        </div>
      )}
      {data?.board && <HouseholdBoard board={data.board} />}
      <div>
        <h2>New Ticket</h2>
        <form onSubmit={createTicket}>
          <label>
            Title:
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </label>
          <label>
            Details:
            <textarea
              value={details}
              onChange={(e) => setDetails(e.target.value)}
            />
          </label>
          <label>
            Priority:
            <select
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
            >
              <option value="low">Low</option>
              <option value="normal">Normal</option>
              <option value="urgent">Urgent</option>
            </select>
          </label>
          <label>
            Due:
            <input
              type="date"
              value={due}
              onChange={(e) => setDue(e.target.value)}
            />
          </label>
          <button type="submit">File Ticket</button>
        </form>
      </div>
      <main>
        <div className="board">
          <div className="column">
            <h3>To Do</h3>
            {data?.dash.todo.map((t: any) => (
              <div key={t.id} className={`card ${t.priority === 'urgent' ? 'urgent' : ''}`}>
                <HoverCard ticket={t}>
                  <div>{t.title}</div>
                </HoverCard>
                <div>{t.priority}</div>
                <div>{t.due}</div>
                {t.status === 'open' && (
                  <button onClick={() => changeStatus(t.id, 'acknowledged')}>Acknowledge</button>
                )}
                {t.status === 'acknowledged' && (
                  <button onClick={() => changeStatus(t.id, 'in_progress')}>Start</button>
                )}
              </div>
            ))}
          </div>
          <div className="column">
            <h3>In Progress</h3>
            {data?.dash.in_progress.map((t: any) => (
              <div key={t.id} className={`card ${t.group === 0 ? 'urgent' : ''}`}>
                <HoverCard ticket={t}>
                  <div>{t.title}</div>
                </HoverCard>
                <div>{t.priority}</div>
                <div>{t.due}</div>
                <button onClick={() => changeStatus(t.id, 'done')}>Done</button>
              </div>
            ))}
          </div>
          <div className="column">
            <h3>Completed</h3>
            {data?.dash.completed.map((t: any) => (
              <div key={t.id} className="card">
                <HoverCard ticket={t}>
                  <div>{t.title}</div>
                </HoverCard>
                <div>{t.priority}</div>
                <div>{t.due}</div>
              </div>
            ))}
          </div>
        </div>
      </main>
      <div>
        <h2>Tickets I Filed</h2>
        {data?.filed.tickets?.map((t: any) => (
          <div key={t.id} className="card">
            <div>{t.title}</div>
            <div>{t.priority}</div>
            <div>{t.due}</div>
            {t.status === 'done' && (
              <>
                <button onClick={() => changeStatus(t.id, 'closed')}>Close</button>
                <button onClick={() => changeStatus(t.id, 'open')}>Reopen</button>
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default App;