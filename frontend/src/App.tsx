import React, { useState } from "react";
import "./styles.css";
import TicketCard from "./TicketCard";
import { fetchDashboard, fetchFiled, createTicket, changeStatus } from "./api";
import { Board, Ticket } from "./types";

const App: React.FC = () => {
  const [token, setToken] = useState("");
  const [board, setBoard] = useState<Board | null>(null);
  const [filed, setFiled] = useState<Ticket[] | null>(null);
  const [error, setError] = useState<string>("");

  // form fields for new ticket
  const [title, setTitle] = useState("");
  const [details, setDetails] = useState("");
  const [priority, setPriority] = useState<"low" | "normal" | "urgent">("normal");
  const [due, setDue] = useState(""); // empty string means null

  const handleLoad = async () => {
    // clear previous state
    setError("");
    setBoard(null);
    setFiled(null);
    if (!token) return;
    try {
      const data = await fetchDashboard(token);
      setBoard(data);
      // also fetch filed tickets on load
      const filedData = await fetchFiled(token);
      setFiled(filedData.tickets);
    } catch (e: any) {
      if (e instanceof Error && e.message === "401") {
        setError("Wrong token");
      } else {
        setError("Something went wrong");
      }
    }
  };

  const handleCreateTicket = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    setError("");
    try {
      await createTicket(token, {
        title,
        details,
        priority,
        due: due === "" ? null : due,
      });
      // on success clear form fields
      setTitle("");
      setDetails("");
      setPriority("normal");
      setDue("");
      // reload dashboard and filed tickets
      const data = await fetchDashboard(token);
      setBoard(data);
      const filedData = await fetchFiled(token);
      setFiled(filedData.tickets);
    } catch (e: any) {
      if (e instanceof Error && e.message === "401") {
        setError("Wrong token");
      } else {
        setError("Something went wrong");
      }
    }
  };

  const handleStatusChange = async (id: number, newStatus: "acknowledged" | "in_progress" | "done") => {
    if (!token) return;
    setError("");
    try {
      await changeStatus(token, id, newStatus);
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

  const handleFileStatusChange = async (id: number, newStatus: "closed" | "open") => {
    if (!token) return;
    setError("");
    try {
      await changeStatus(token, id, newStatus);
      // reload both board and filed tickets
      const boardData = await fetchDashboard(token);
      setBoard(boardData);
      const filedData = await fetchFiled(token);
      setFiled(filedData.tickets);
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
          tickets.map((t) => (
            <TicketCard key={t.id} ticket={t}>
              {t.status === "open" && (
                <button type="button" onClick={() => handleStatusChange(t.id, "acknowledged")}>Acknowledge</button>
              )}
              {t.status === "acknowledged" && (
                <button type="button" onClick={() => handleStatusChange(t.id, "in_progress")}>Start</button>
              )}
              {t.status === "in_progress" && (
                <button type="button" onClick={() => handleStatusChange(t.id, "done")}>Done</button>
              )}
            </TicketCard>
          ))
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
        {/* New ticket form */}
        <section className="panel new-ticket" aria-label="New ticket">
          <h2>New ticket for {token ? (token.includes("her") ? "him" : "her") : ""}</h2>
          <form onSubmit={handleCreateTicket}>
            <label>
              Title
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                name="title"
              />
            </label>
            <label>
              Details
              <textarea
                value={details}
                onChange={(e) => setDetails(e.target.value)}
                name="details"
              />
            </label>
            <label>
              Priority
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value as "low" | "normal" | "urgent")}
                name="priority"
              >
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
                name="due"
              />
            </label>
            <button type="submit">File ticket</button>
          </form>
        </section>
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
        {filed && (
          <section className="panel" aria-label="Tickets I filed">
            <h2>Tickets I filed</h2>
            <div className="card-list">
              {filed.map((t) => (
                <TicketCard key={t.id} ticket={t}>
                  {t.status === "done" && (
                    <>
                      <button type="button" onClick={() => handleFileStatusChange(t.id, "closed")}>Close</button>
                      <button type="button" onClick={() => handleFileStatusChange(t.id, "open")}>Reopen</button>
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

