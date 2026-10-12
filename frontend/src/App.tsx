import { useState } from "react";
import "./styles.css";
import type { Board, Filed, NewTicket, Ticket } from "./types";
import { changeStatus, createTicket, fetchDashboard, fetchFiled } from "./api";
import TicketCard from "./TicketCard";

export default function App() {
  const [token, setToken] = useState("");
  const [board, setBoard] = useState<Board | null>(null);
  const [filed, setFiled] = useState<Filed | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [user, setUser] = useState<"her" | "him" | null>(null);

  // New ticket form state
  const [title, setTitle] = useState("");
  const [details, setDetails] = useState("");
  const [priority, setPriority] = useState<"low" | "normal" | "urgent">("normal");
  const [due, setDue] = useState("");

  async function handleLoad() {
    setError(null);
    try {
      const [dash, fld] = await Promise.all([
        fetchDashboard(token),
        fetchFiled(token).catch(() => ({ tickets: [] as Ticket[] })),
      ]);
      setBoard(dash);
      setFiled(fld);
    } catch (e) {
      const err = e as Error;
      if (err.message === "401") {
        setError("Wrong token");
      } else {
        setError("Something went wrong");
      }
      setBoard(null);
      setFiled(null);
    }
  }

  async function handleFileTicket() {
    if (!title.trim()) return;
    setError(null);
    try {
      const data: NewTicket = {
        title: title.trim(),
        details,
        priority,
        due: due || null,
      };
      await createTicket(token, data);
      setTitle("");
      setDetails("");
      setPriority("normal");
      setDue("");
      await handleLoad();
    } catch (e) {
      const err = e as Error;
      if (err.message === "401") {
        setError("Wrong token");
      } else {
        setError("Something went wrong");
      }
    }
  }

  async function handleStatusChange(id: number, status: string) {
    setError(null);
    try {
      await changeStatus(token, id, status);
      await handleLoad();
    } catch (e) {
      const err = e as Error;
      if (err.message === "401") {
        setError("Wrong token");
      } else {
        setError("Something went wrong");
      }
    }
  }

  function renderColumn(name: string, ariaLabel: string, tickets: Ticket[]) {
    return (
      <section className="column" aria-label={ariaLabel}>
        <h3 className="column-title">
          {name} <span className="count">{tickets.length}</span>
        </h3>
        {tickets.length === 0 ? (
          <p className="empty">Nothing here</p>
        ) : (
          tickets.map((t) => (
            <TicketCard key={t.id} ticket={t}>
              {t.status === "open" && (
                <button onClick={() => handleStatusChange(t.id, "acknowledged")}>Acknowledge</button>
              )}
              {t.status === "acknowledged" && (
                <button onClick={() => handleStatusChange(t.id, "in_progress")}>Start</button>
              )}
              {t.status === "in_progress" && (
                <button onClick={() => handleStatusChange(t.id, "done")}>Done</button>
              )}
            </TicketCard>
          ))
        )}
      </section>
    );
  }

  return (
    <div className="app">
      <header className="topbar">
        <h1 className="brand">~/honey-do</h1>
        <div className="token-form">
          <label>
            Token
            <input
              type="password"
              value={token}
              onChange={(e) => setToken(e.target.value)}
            />
          </label>
          <button onClick={handleLoad}>Load</button>
        </div>
      </header>
      <main className="content">
        {error && <p role="alert" className="error">{error}</p>}
        {board && (
          <section className="panel new-ticket" aria-label="New ticket">
            <h2>New ticket</h2>
            <form onSubmit={(e) => { e.preventDefault(); handleFileTicket(); }}>
              <label>
                Title
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                />
              </label>
              <label>
                Details
                <textarea
                  value={details}
                  onChange={(e) => setDetails(e.target.value)}
                />
              </label>
              <label>
                Priority
                <select value={priority} onChange={(e) => setPriority(e.target.value as "low" | "normal" | "urgent")}>
                  <option value="low">low</option>
                  <option value="normal">normal</option>
                  <option value="urgent">urgent</option>
                </select>
              </label>
              <label>
                Due
                <input
                  type="date"
                  value={due}
                  onChange={(e) => setDue(e.target.value)}
                />
              </label>
              <button type="submit">File ticket</button>
            </form>
          </section>
        )}
        {board && (
          <section className="panel" aria-label="My board">
            <h2>My board</h2>
            <div className="board">
              {renderColumn("To Do", "To Do", board.todo)}
              {renderColumn("In Progress", "In Progress", board.in_progress)}
              {renderColumn("Completed", "Completed", board.completed)}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}