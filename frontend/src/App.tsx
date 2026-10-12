import { useState } from "react";
import "./styles.css";
import type { Board, NewTicket, Ticket } from "./types";
import { changeStatus, createTicket, fetchDashboard, fetchFiled } from "./api";
import TicketCard from "./TicketCard";

export default function App() {
  const [token, setToken] = useState("");
  const [board, setBoard] = useState<Board | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [details, setDetails] = useState("");
  const [priority, setPriority] = useState<"low" | "normal" | "urgent">("normal");
  const [due, setDue] = useState("");

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

  async function handleFileTicket() {
    setError(null);
    const payload: NewTicket = {
      title,
      details,
      priority,
      due: due === "" ? null : due,
    };
    try {
      await createTicket(token, payload);
      setTitle("");
      setDetails("");
      setPriority("normal");
      setDue("");
      await handleLoad();
    } catch (e) {
      if (e instanceof Error && e.message === "401") {
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
      if (e instanceof Error && e.message === "401") {
        setError("Wrong token");
      } else {
        setError("Something went wrong");
      }
    }
  }

  function renderColumn(name: string, ariaLabel: string, tickets: Ticket[]) {
    const buttons = tickets.map((t) => {
      let button: React.ReactNode = null;
      if (name === "To Do") {
        if (t.status === "open") {
          button = (
            <button onClick={() => handleStatusChange(t.id, "acknowledged")}>
              Acknowledge
            </button>
          );
        } else if (t.status === "acknowledged") {
          button = (
            <button onClick={() => handleStatusChange(t.id, "in_progress")}>
              Start
            </button>
          );
        }
      } else if (name === "In Progress" && t.status === "in_progress") {
        button = (
          <button onClick={() => handleStatusChange(t.id, "done")}>
            Done
          </button>
        );
      }
      return (
        <TicketCard key={t.id} ticket={t}>
          {button}
        </TicketCard>
      );
    });

    return (
      <section className="column" aria-label={ariaLabel}>
        <h3 className="column-title">
          {name} <span className="count">{tickets.length}</span>
        </h3>
        {tickets.length === 0 ? (
          <p className="empty">Nothing here</p>
        ) : (
          buttons
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
          <>
            <section className="panel new-ticket" aria-label="New ticket">
              <h2>New ticket</h2>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  handleFileTicket();
                }}
              >
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
                  <select
                    value={priority}
                    onChange={(e) => setPriority(e.target.value as "low" | "normal" | "urgent")}
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
                  />
                </label>
                <button type="submit">File ticket</button>
              </form>
            </section>
            <section className="panel" aria-label="My board">
              <h2>My board</h2>
              <div className="board">
                {renderColumn("To Do", "To Do", board.todo)}
                {renderColumn("In Progress", "In Progress", board.in_progress)}
                {renderColumn("Completed", "Completed", board.completed)}
              </div>
            </section>
          </>
        )}
      </main>
    </div>
  );
}