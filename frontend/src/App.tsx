import { useState } from "react";
import "./styles.css";
import type { Board, Ticket } from "./types";
import { fetchDashboard, fetchFiled } from "./api";
import TicketCard from "./TicketCard";

export default function App() {
  const [token, setToken] = useState("");
  const [board, setBoard] = useState<Board | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleLoad() {
    setError(null);
    try {
      const [dash] = await Promise.all([
        fetchDashboard(token),
        fetchFiled(token).catch(() => ({ tickets: [] as Ticket[] })),
      ]);
      setBoard(dash);
    } catch (e) {
      if (e instanceof Error && e.message === "401") {
        setError("Wrong token");
      } else {
        setError("Something went wrong");
      }
      setBoard(null);
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
          tickets.map((t) => <TicketCard key={t.id} ticket={t} />)
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