import React, { useState } from "react";
import "./styles.css";
import TicketCard from "./TicketCard";
import { fetchDashboard } from "./api";
import { Board, Ticket } from "./types";

const App: React.FC = () => {
  const [token, setToken] = useState("");
  const [board, setBoard] = useState<Board | null>(null);
  const [error, setError] = useState<string>("");

  const handleLoad = async () => {
    // clear previous state
    setError("");
    setBoard(null);
    if (!token) return;
    try {
      const data = await fetchDashboard(token);
      setBoard(data);
    } catch (e: any) {
      if (e instanceof Error && e.message === "401") {
        setError("Wrong token");
      } else {
        setError("Something went wrong");
      }
    }
  };

  const renderColumn = (name: string, tickets: Ticket[]) => {
    const count = tickets.length;
    return (
      <section className="column" aria-label={name} key={name}>
        <h3 className="column-title">
          {name} <span className="count">{count}</span>
        </h3>
        {count > 0 ? (
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
        <label>
          Token
          <input
            type="password"
            value={token}
            onChange={(e) => setToken(e.target.value)}
          />
        </label>
        <button type="button" onClick={handleLoad}>Load</button>
      </header>
      <main className="content">
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
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
};

export default App;
