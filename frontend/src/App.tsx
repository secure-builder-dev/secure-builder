import { useState } from "react";
import type { Board, NewTicket, Ticket, User } from "./types";
import { changeStatus, createTicket, fetchBoard, fetchDashboard, fetchFiled, fetchMe } from "./api";
import Directions from "./Directions";
import HouseholdBoard from "./HouseholdBoard";
import Menu from "./Menu";
import TicketCard from "./TicketCard";
import TicketDetail from "./TicketDetail";

const COLUMNS: Array<{ key: keyof Board; label: string }> = [
  { key: "todo", label: "To Do" },
  { key: "in_progress", label: "In Progress" },
  { key: "completed", label: "Completed" },
];

const EMPTY_FORM: NewTicket = { title: "", details: "", priority: "normal", due: null };

export default function App() {
  const [token, setToken] = useState("");
  const [board, setBoard] = useState<Board | null>(null);
  const [household, setHousehold] = useState<Board | null>(null);
  const [filed, setFiled] = useState<Ticket[]>([]);
  const [me, setMe] = useState<User | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState<NewTicket>(EMPTY_FORM);
  const [showDirections, setShowDirections] = useState(false);
  const [openTicket, setOpenTicket] = useState<Ticket | null>(null);
  const [historyTick, setHistoryTick] = useState(0);

  function fail(e: unknown) {
    if (e instanceof Error && e.message === "401") {
      setError("Wrong token");
    } else {
      setError("Something went wrong");
    }
  }

  function isBoard(v: unknown): v is Board {
    return (
      typeof v === "object" &&
      v !== null &&
      Array.isArray((v as Board).todo) &&
      Array.isArray((v as Board).in_progress) &&
      Array.isArray((v as Board).completed)
    );
  }

  async function refresh() {
    try {
      const dash = await fetchDashboard(token);
      setBoard(dash);
      const f = await fetchFiled(token);
      setFiled(f.tickets);
    } catch (e) {
      setBoard(null);
      setFiled([]);
      fail(e);
    }
    try {
      const b = await fetchBoard(token);
      if (isBoard(b)) {
        setHousehold(b);
      } else {
        setHousehold(null);
      }
    } catch {
      setHousehold(null);
    }
  }

  async function load() {
    setError(null);
    setMe(null);
    setOpenTicket(null);
    setHistoryTick(0);
    void (async () => {
      try {
        const m = await fetchMe(token);
        if (m && (m.user === "her" || m.user === "him")) {
          setMe(m.user);
        }
      } catch {
        // a failed or malformed /api/me leaves the whoami empty
      }
    })();
    await refresh();
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
      if (openTicket && openTicket.id === ticket.id) {
        setHistoryTick((t) => t + 1);
      }
      await refresh();
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

  function filedActionsFor(t: Ticket) {
    if (t.status !== "done") {
      return null;
    }
    return (
      <>
        <button type="button" onClick={() => void move(t, "closed")}>Close</button>{" "}
        <button type="button" onClick={() => void move(t, "open")}>Reopen</button>
      </>
    );
  }

  return (
    <div className="app">
      <header className="topbar">
        <h1 className="brand">~/honey-do</h1>
        <Menu onDirections={() => setShowDirections(true)} />
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
        {me && <span className="whoami">Signed in as {me}</span>}
      </header>
      <main className="content">
        {error && (
          <p role="alert" className="error">{error}</p>
        )}
        {showDirections && <Directions onClose={() => setShowDirections(false)} />}
        {openTicket && (
          <TicketDetail
            token={token}
            ticket={openTicket}
            me={me}
            historyTick={historyTick}
            onClose={() => setOpenTicket(null)}
          />
        )}
        <section className="panel new-ticket" aria-label="New ticket">
          <h2>{me === "her" ? "New ticket for him" : me === "him" ? "New ticket for her" : "New ticket"}</h2>
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
                          <TicketCard key={t.id} ticket={t} onOpen={setOpenTicket}>
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
        {board && (
          <section className="panel" aria-label="Tickets I filed">
            <h2>Tickets I filed</h2>
            <div className="card-list">
              {filed.map((t) => {
                const actions = filedActionsFor(t);
                return (
                  <TicketCard key={t.id} ticket={t} onOpen={setOpenTicket}>
                    {actions}
                  </TicketCard>
                );
              })}
            </div>
          </section>
        )}
        {household && <HouseholdBoard board={household} onOpen={setOpenTicket} />}
      </main>
    </div>
  );
}