import { useState } from "react";
import type { Board, NewTicket, Ticket } from "./types";
import { changeStatus, createTicket, fetchDashboard, fetchFiled } from "./api";
import TicketCard from "./TicketCard";

const COLUMNS: Array<{ key: keyof Board; label: string }> = [
  { key: "todo", label: "To Do" },
  { key: "in_progress", label: "In Progress" },
  { key: "completed", label: "Completed" },
];

const EMPTY_FORM: NewTicket = { title: "", details: "", priority: "normal", due: null };

export default function App() {
  const [token, setToken] = useState("");
  const [board, setBoard] = useState<Board | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState<NewTicket>(EMPTY_FORM);

  function fail(e: unknown) {
    if (e instanceof Error && e.message === "401") {
      setError("Wrong token");
    } else {
      setError("Something went wrong");
    }
  }

  async function load() {
    setError(null);
    try {
      const dash = await fetchDashboard(token);
      setBoard(dash);
      await fetchFiled(token);
    } catch (e) {
      setBoard(null);
      fail(e);
    }
  }

  async function fileTicket() {
    setError(null);
    try {
      await createTicket(token, form);
      setForm(EMPTY_FORM);
      await load();
    } catch (e) {
      fail(e);
    }
  }

  async function move(ticket: Ticket, status: string) {
    setError(null);
    try {
      await changeStatus(token, ticket.id, status);
      await load();
    } catch (e) {
      fail(e);
    }
  }

  function actionsFor(t: Ticket) {
    if (t.status === "open") {
      return <button type="button" onClick={() => void move(t, "acknowledged")}>Acknowledge</button>;
    }
    if (t.status === "acknowledged") {
      return <button type="button" onClick={() => void move(t, "in_progress")}>Start</button>;
    }
    if (t.status === "in_progress") {
      return <button type="button" onClick={() => void move(t, "done")}>Done</button>;
    }
    return null;
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
        <section className="panel new-ticket" aria-label="New ticket">
          <h2>New ticket</h2>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void fileTicket();
            }}
          >
            <label>
              Title{" "}
              <input
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
              />
            </label>{" "}
            <label>
              Details{" "}
              <textarea
                value={form.details}
                onChange={(e) => setForm({ ...form, details: e.target.value })}
              />
            </label>{" "}
            <label>
              Priority{" "}
              <select
                value={form.priority}
                onChange={(e) =>
                  setForm({ ...form, priority: e.target.value as NewTicket["priority"] })
                }
              >
                <option value="low">low</option>
                <option value="normal">normal</option>
                <option value="urgent">urgent</option>
              </select>
            </label>{" "}
            <label>
              Due{" "}
              <input
                type="date"
                value={form.due ?? ""}
                onChange={(e) => setForm({ ...form, due: e.target.value || null })}
              />
            </label>{" "}
            <button type="submit">File ticket</button>
          </form>
        </section>
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
                      tickets.map((t) => {
                        const actions = actionsFor(t);
                        return (
                          <TicketCard key={t.id} ticket={t}>
                            {actions}
                          </TicketCard>
                        );
                      })
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