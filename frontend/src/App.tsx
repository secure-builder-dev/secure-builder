// Updated App component with Menu, Directions, FilterBar, and SummaryBadge integration
import React, { useState, FormEvent } from "react";
import "./styles.css";
import TicketCard from "./TicketCard";
import HouseholdBoard from "./HouseholdBoard";
import Menu from "./Menu";
import Directions from "./Directions";
import TicketDetail from "./TicketDetail";
import FilterBar from "./FilterBar";
import SummaryBadge from "./SummaryBadge";
import { fetchDashboard, fetchFiled, fetchBoard, createTicket, changeStatus, fetchMe, fetchHistory, fetchSummary } from "./api";
import { Board, Ticket, Me, Status, User } from "./types";

const App = () => {
  // authentication and UI state
  const [token, setToken] = useState<string>("");
  const [me, setMe] = useState<User | null>(null);
  const [error, setError] = useState<string>("");
  const [showDirections, setShowDirections] = useState<boolean>(false);

  // data fetched from the API
  const [board, setBoard] = useState<Board | null>(null);
  const [filed, setFiled] = useState<Ticket[] | null>(null);
  const [householdBoard, setHouseholdBoard] = useState<Board | null>(null);
  const [summary, setSummary] = useState<{ overdue: number; due_today: number; open: number } | null>(null);

  // currently opened ticket in the detail panel
  const [openedTicket, setOpenedTicket] = useState<Ticket | null>(null);

  // form fields for creating a new ticket
  const [title, setTitle] = useState<string>("");
  const [details, setDetails] = useState<string>("");
  const [priority, setPriority] = useState<string>("normal");
  const [due, setDue] = useState<string>(""); // empty string means null

  // filter state for household board
  const [boardFilter, setBoardFilter] = useState<{ q: string; priority: string; assigned_to: string }>({
    q: "",
    priority: "",
    assigned_to: "",
  });

  const handleLoad = async () => {
    // reset everything on load
    setError("");
    setBoard(null);
    setFiled(null);
    setHouseholdBoard(null);
    setOpenedTicket(null);
    setMe(null);
    setSummary(null);
    setShowDirections(false);
    if (!token) return;
    try {
      // who am I?
      try {
        const meResp = await fetchMe(token);
        setMe(meResp.user);
      } catch (_) {
        setMe(null);
      }
      const dash = await fetchDashboard(token);
      setBoard(dash);
      const filedData = await fetchFiled(token);
      setFiled(filedData.tickets);
    // fetch household board with current filter (initially empty)
    try {
      const hb = await fetchBoard(token, boardFilter);
      const valid = hb && Array.isArray(hb.todo) && Array.isArray(hb.in_progress) && Array.isArray(hb.completed);
      setHouseholdBoard(valid ? hb : null);
    } catch (_) {
      // board fetch failure should not set an error alert; just hide the board
      setHouseholdBoard(null);
    }
    // fetch summary
    try {
      const sum = await fetchSummary(token);
      if (
        typeof sum.overdue === "number" &&
        typeof sum.due_today === "number" &&
        typeof sum.open === "number"
      ) {
        setSummary(sum);
      } else {
        setSummary(null);
      }
    } catch (_) {
      setSummary(null);
    }
    } catch (e) {
      if (e instanceof Error && e.message === "401") {
        setError("Wrong token");
      } else {
        setError("Something went wrong");
      }
    }
  };

  const handleCreateTicket = async (e: FormEvent) => {
    e.preventDefault();
    if (!token) return;
    setError("");
    try {
      await createTicket(token, {
        title,
        details,
        priority: priority as "low" | "normal" | "urgent",
        due: due === "" ? null : due,
      });
      // clear form
      setTitle("");
      setDetails("");
      setPriority("normal");
      setDue("");
      // reload data
      const dash = await fetchDashboard(token);
      setBoard(dash);
      try {
        const hb = await fetchBoard(token, boardFilter);
        const valid = hb && Array.isArray(hb.todo) && Array.isArray(hb.in_progress) && Array.isArray(hb.completed);
        setHouseholdBoard(valid ? hb : null);
      } catch (_) {
        setHouseholdBoard(null);
      }
      const filedData = await fetchFiled(token);
      setFiled(filedData.tickets);
      // refresh summary
      try {
        const sum = await fetchSummary(token);
        if (
          typeof sum.overdue === "number" &&
          typeof sum.due_today === "number" &&
          typeof sum.open === "number"
        ) {
          setSummary(sum);
        } else {
          setSummary(null);
        }
      } catch (_) {
        setSummary(null);
      }
    } catch (e) {
      if (e instanceof Error && e.message === "401") {
        setError("Wrong token");
      } else {
        setError("Something went wrong");
      }
    }
  };

  const handleStatusChange = async (id: number, newStatus: Status) => {
    if (!token) return;
    setError("");
    try {
      await changeStatus(token, id, newStatus);
      const dash = await fetchDashboard(token);
      setBoard(dash);
      // refresh household board with current filter
      try {
        const hb = await fetchBoard(token, boardFilter);
        const valid = hb && Array.isArray(hb.todo) && Array.isArray(hb.in_progress) && Array.isArray(hb.completed);
        setHouseholdBoard(valid ? hb : null);
      } catch (_) {
        setHouseholdBoard(null);
      }
      // if the open detail panel shows this ticket, refresh its history
      if (openedTicket && openedTicket.id === id) {
        await fetchHistory(token, id);
      }
      // refresh summary
      try {
        const sum = await fetchSummary(token);
        if (
          typeof sum.overdue === "number" &&
          typeof sum.due_today === "number" &&
          typeof sum.open === "number"
        ) {
          setSummary(sum);
        } else {
          setSummary(null);
        }
      } catch (_) {
        setSummary(null);
      }
    } catch (e) {
      if (e instanceof Error && e.message === "401") {
        setError("Wrong token");
      } else {
        setError("Something went wrong");
      }
    }
  };

  const handleFileStatusChange = async (id: number, newStatus: Status) => {
    if (!token) return;
    setError("");
    try {
      await changeStatus(token, id, newStatus);
      const dash = await fetchDashboard(token);
      setBoard(dash);
      const filedData = await fetchFiled(token);
      setFiled(filedData.tickets);
      // also refresh household board with current filter
      try {
        const hb = await fetchBoard(token, boardFilter);
        const valid = hb && Array.isArray(hb.todo) && Array.isArray(hb.in_progress) && Array.isArray(hb.completed);
        setHouseholdBoard(valid ? hb : null);
      } catch (_) {
        setHouseholdBoard(null);
      }
      // refresh history if open
      if (openedTicket && openedTicket.id === id) {
        await fetchHistory(token, id);
      }
      // refresh summary
      try {
        const sum = await fetchSummary(token);
        if (
          typeof sum.overdue === "number" &&
          typeof sum.due_today === "number" &&
          typeof sum.open === "number"
        ) {
          setSummary(sum);
        } else {
          setSummary(null);
        }
      } catch (_) {
        setSummary(null);
      }
    } catch (e) {
      if (e instanceof Error && e.message === "401") {
        setError("Wrong token");
      } else {
        setError("Something went wrong");
      }
    }
  };

  const handleDirections = () => setShowDirections(true);
  const handleCloseDirections = () => setShowDirections(false);

  const openTicket = (ticket: Ticket) => {
    setOpenedTicket(ticket);
  };

  const handleTicketSaved = async (saved: Ticket) => {
    // re-fetch data after a successful edit, similar to other handlers
    if (!token) return;
    setError("");
    try {
      const dash = await fetchDashboard(token);
      setBoard(dash);
      const filedData = await fetchFiled(token);
      setFiled(filedData.tickets);
      const hb = await fetchBoard(token, boardFilter);
      const valid = hb && Array.isArray(hb.todo) && Array.isArray(hb.in_progress) && Array.isArray(hb.completed);
      setHouseholdBoard(valid ? hb : null);
      const sum = await fetchSummary(token);
      if (
        typeof sum.overdue === "number" &&
        typeof sum.due_today === "number" &&
        typeof sum.open === "number"
      ) {
        setSummary(sum);
      } else {
        setSummary(null);
      }

    } catch (e) {
      if (e instanceof Error && e.message === "401") {
        setError("Wrong token");
      } else {
        setError("Something went wrong");
      }
    }
  };
  const closeTicketDetail = () => {
    setOpenedTicket(null);
  };

  const applyFilter = (filter: { q: string; priority: string; assigned_to: string }) => {
    const cleaned = {
      q: filter.q.trim(),
      priority: filter.priority,
      assigned_to: filter.assigned_to,
    };
    setBoardFilter(cleaned);
    // fetch board with new filter
    fetchBoard(token, cleaned)
      .then((hb) => {
        const valid = hb && Array.isArray(hb.todo) && Array.isArray(hb.in_progress) && Array.isArray(hb.completed);
        setHouseholdBoard(valid ? hb : null);
      })
      .catch(() => {
        setHouseholdBoard(null);
      });
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
            <TicketCard key={t.id} ticket={t} onOpen={openTicket}>
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
        <Menu onDirections={handleDirections} />
        <label>
          Token
          <input
            type="password"
            value={token}
            onChange={(e) => setToken(e.target.value)}
          />
        </label>
        <button type="button" onClick={handleLoad}>Load</button>
        {me && <span className="whoami">Signed in as {me}</span>}
        {summary && <SummaryBadge summary={summary} />}
      </header>
      <main className="content">
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        {showDirections && <Directions onClose={handleCloseDirections} />}
        {/* Ticket detail panel – appears after directions and before new ticket */}
        {openedTicket && (
          <TicketDetail
            token={token}
            ticket={openedTicket}
            me={me}
            onClose={closeTicketDetail} onSaved={handleTicketSaved}
          />
        )}
        {/* New ticket form */}
        <section className="panel new-ticket" aria-label="New ticket">
          <h2>{me ? `New ticket for ${me === "her" ? "him" : "her"}` : "New ticket"}</h2>
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
                onChange={(e) => setPriority(e.target.value)}
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
                <TicketCard key={t.id} ticket={t} onOpen={openTicket}>
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
        {householdBoard && (
          <HouseholdBoard board={householdBoard} onOpen={openTicket}>
            <FilterBar onApply={applyFilter} />
          </HouseholdBoard>
        )}
      </main>
    </div>
  );
};

export default App;
