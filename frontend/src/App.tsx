import React, { useState } from "react";
import TicketCard from "./TicketCard";
import HouseholdBoard from "./HouseholdBoard";
import Menu from "./Menu";
import Directions from "./Directions";
import { fetchDashboard, fetchFiled, fetchBoard, changeStatus, createTicket, fetchMe } from "./api";
import type { Board, Ticket } from "./types";


export default function App() {
  const [token, setToken] = useState("");
const [me, setMe] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [board, setBoard] = useState<Board | null>(null);
  const [houseBoard, setHouseBoard] = useState<Board | null>(null);
  const [filed, setFiled] = useState<Ticket[] | null>(null);
  const [showDirections, setShowDirections] = useState(false);

  const openDirections = () => setShowDirections(true);
  const closeDirections = () => setShowDirections(false);

  // form state for new ticket
  const [title, setTitle] = useState("");
  const [details, setDetails] = useState("");
  const [priority, setPriority] = useState<"low" | "normal" | "urgent">("normal");
  const [due, setDue] = useState(""); // empty string means no date

  const handleLoad = async () => {
    // clear previous state
    setError(null);
    setBoard(null);
    setFiled(null);
    setMe(null);
    try {
      // first, fetch who we are
      try {
        const meResp = await fetchMe(token);
        if (meResp && (meResp.user === "her" || meResp.user === "him")) {
          setMe(meResp.user);
        } else {
          setMe(null);
        }
      } catch {
        // ignore errors – no whoami shown, no error message
        setMe(null);
      }

      const dash = await fetchDashboard(token);
      setBoard(dash);
      const f = await fetchFiled(token);
      setFiled(f.tickets);
      try {
        const hb = await fetchBoard(token);
        if (
          hb &&
          Array.isArray(hb.todo) &&
          Array.isArray(hb.in_progress) &&
          Array.isArray(hb.completed)
        ) {
          setHouseBoard(hb);
        } else {
          setHouseBoard(null);
        }
      } catch {
        // Silently ignore board fetch errors; no error message shown.
        setHouseBoard(null);
      }
    } catch (e: any) {
      if (e instanceof Error && e.message === "401") {
        setError("Wrong token");
      } else {
        setError("Something went wrong");
      }
    }
  };

  const handleStatusChange = async (id: number, newStatus: string) => {
    try {
      await changeStatus(token, id, newStatus);
      // reload after a successful move
      await handleLoad();
    } catch (e: any) {
      if (e instanceof Error && e.message === "401") {
        setError("Wrong token");
      } else {
        setError("Something went wrong");
      }
    }
  };

  const handleFileTicket = async () => {
    try {
      await createTicket(token, {
        title,
        details,
        priority,
        due: due === "" ? null : due,
      });
      // clear form fields on success
      setTitle("");
      setDetails("");
      setPriority("normal");
      setDue("");
      // reload board and filed tickets
      await handleLoad();
    } catch (e: any) {
      if (e instanceof Error && e.message === "401") {
        setError("Wrong token");
      } else {
        setError("Something went wrong");
      }
    }
  };

  const renderBoardActions = (ticket: Ticket) => {
    if (ticket.status === "open") {
      return (
        <button onClick={() => handleStatusChange(ticket.id, "acknowledged")}>Acknowledge</button>
      );
    }
    if (ticket.status === "acknowledged") {
      return (
        <button onClick={() => handleStatusChange(ticket.id, "in_progress")}>Start</button>
      );
    }
    if (ticket.status === "in_progress") {
      return (
        <button onClick={() => handleStatusChange(ticket.id, "done")}>Done</button>
      );
    }
    return null;
  };

  const renderFiledActions = (ticket: Ticket) => {
    if (ticket.status === "done") {
      return (
        <>
          <button onClick={() => handleStatusChange(ticket.id, "closed")}>Close</button>
          <button onClick={() => handleStatusChange(ticket.id, "open")}>Reopen</button>
        </>
      );
    }
    return null;
  };

  const renderColumn = (label: string, tickets: Ticket[]) => {
    return (
      <section className="column" aria-label={label}>
        <h3 className="column-title">
          {label} <span className="count">{tickets.length}</span>
        </h3>
        {tickets.length > 0 ? (
          tickets.map((t) => (
            <TicketCard key={t.id} ticket={t}>
              {renderBoardActions(t)}
            </TicketCard>
          ))
        ) : (
          <p className="empty">Nothing here</p>
        )}
      </section>
    );
  };

  const renderFiledPanel = () => {
    if (!filed) return null;
    return (
      <section className="panel" aria-label="Tickets I filed">
        <h2>Tickets I filed</h2>
        <div className="card-list">
          {filed.map((t) => (
            <TicketCard key={t.id} ticket={t}>
              {renderFiledActions(t)}
            </TicketCard>
          ))}
        </div>
      </section>
    );
  };

  return (
    <div className="app">
      <header className="topbar" role="banner">
        <h1 className="brand">~/honey-do</h1>
        <Menu onDirections={openDirections} />
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
        {me && <span className="whoami">Signed in as {me}</span>}
      </header>
      <main className="content">
        {error && <p role="alert" className="error">{error}</p>}
        {showDirections && <Directions onClose={closeDirections} />}
        {/* New ticket panel */}
        <section className="panel new-ticket" aria-label="New ticket">
          <h2>{me ? `New ticket for ${me === "her" ? "him" : "her"}` : "New ticket"}</h2>
          <form>
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
            <button type="button" onClick={handleFileTicket}>File ticket</button>
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
        {renderFiledPanel()}
        {houseBoard && (
          <HouseholdBoard board={houseBoard} />
        )}
      </main>
    </div>
  );
}
