import React, { useState } from "react";
import TicketCard from "./TicketCard";
import { fetchDashboard, fetchFiled } from "./api";
import type { Board, Ticket } from "./types";

export default function App() {
  const [token, setToken] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [board, setBoard] = useState<Board | null>(null);

  const handleLoad = async () => {
    // clear previous state
    setError(null);
    setBoard(null);
    try {
      const dash = await fetchDashboard(token);
      setBoard(dash);
      // optional: also fetch filed tickets to keep future beads happy
      await fetchFiled(token);
    } catch (e: any) {
      if (e instanceof Error && e.message === "401") {
        setError("Wrong token");
      } else {
        setError("Something went wrong");
      }
    }
  };

  const renderColumn = (label: string, tickets: Ticket[]) => {
    return (
      <section className="column" aria-label={label}>
        <h3 className="column-title">
          {label} <span className="count">{tickets.length}</span>
        </h3>
        {tickets.length > 0 ? (
          tickets.map((t) => <TicketCard key={t.id} ticket={t} />)
        ) : (
          <p className="empty">Nothing here</p>
        )}
      </section>
    );
  };

  return (
    <div className="app">
      <header className="topbar" role="banner">
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
          <button type="button" onClick={handleLoad}>Load</button>
        </div>
      </header>
      <main className="content">
        {error && <p role="alert" className="error">{error}</p>}
        {board && (
          <section className="panel" aria-label="My board">
            <h2>My board</h2>
            <div className="board">
              {renderColumn("To Do", board.todo)}
              {renderColumn("In Progress", board.in_progress)}
              {renderColumn("Completed", board.completed)}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
