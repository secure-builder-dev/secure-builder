import { useState } from "react";
import type { Board, Ticket } from "./types";
import { fetchDashboard, fetchFiled } from "./api";
import TicketCard from "./TicketCard";

const COLUMNS: Array<{ key: keyof Board; label: string }> = [
  { key: "todo", label: "To Do" },
  { key: "in_progress", label: "In Progress" },
  { key: "completed", label: "Completed" },
];

export default function App() {
  const [token, setToken] = useState("");
  const [board, setBoard] = useState<Board | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setError(null);
    try {
      const dash = await fetchDashboard(token);
      setBoard(dash);
      await fetchFiled(token);
    } catch (e) {
      setBoard(null);
      if (e instanceof Error && e.message === "401") {
        setError("Wrong token");
      } else {
        setError("Something went wrong");
      }
    }
  }

  return (
    <div className="app">
      <header className="topbar">
        <h1 className="brand">~/honey-do</h1>
        <div className="token-form">
          <label>
            Token{" "}
            <input
              type="password"
              value={token}
              onChange={(e) => setToken(e.target.value)}
            />
          </label>{" "}
          <button type="button" onClick={() => void load()}>Load</button>
        </div>
      </header>
      <main className="content">
        {error && (
          <p role="alert" className="error">{error}</p>
        )}
        {board && (
          <section className="panel" aria-label="My board">
            <h2>My board</h2>
            <div className="board">
              {COLUMNS.map(({ key, label }) => {
                const tickets: Ticket[] = board[key];
                return (
                  <section key={key} className="column" aria-label={label}>
                    <h3 className="column-title">
                      {label} <span className="count">{tickets.length}</span>
                    </h3>
                    {tickets.length === 0 ? (
                      <p className="empty">Nothing here</p>
                    ) : (
                      tickets.map((t) => <TicketCard key={t.id} ticket={t} />)
                    )}
                  </section>
                );
              })}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
