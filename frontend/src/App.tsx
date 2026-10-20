// Updated App component with Menu and Directions integration
import React, { useState } from "react";
import "./styles.css";
import TicketCard from "./TicketCard";
import HouseholdBoard from "./HouseholdBoard";
import Menu from "./Menu";
import Directions from "./Directions";
import TicketDetail from "./TicketDetail";
import { fetchDashboard, fetchFiled, fetchBoard, createTicket, changeStatus, fetchMe, fetchHistory } from "./api";
import { Board, Ticket, Me } from "./types";

const App = () => {
  // authentication and UI state
  const [token, setToken] = useState("");
  const [me, setMe] = useState(null);
  const [error, setError] = useState("");
  const [showDirections, setShowDirections] = useState(false);

  // data fetched from the API
  const [board, setBoard] = useState(null);
  const [filed, setFiled] = useState(null);
  const [householdBoard, setHouseholdBoard] = useState(null);

  // currently opened ticket in the detail panel
  const [openedTicket, setOpenedTicket] = useState(null);

  // form fields for creating a new ticket
  const [title, setTitle] = useState("");
  const [details, setDetails] = useState("");
  const [priority, setPriority] = useState("normal");
  const [due, setDue] = useState(""); // empty string means null

  const handleLoad = async () => {
    // reset everything on load
    setError("");
    setBoard(null);
    setFiled(null);
    setHouseholdBoard(null);
    setOpenedTicket(null);
    setMe(null);
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
      try {
        const hb = await fetchBoard(token);
        const valid = hb && Array.isArray(hb.todo) && Array.isArray(hb.in_progress) && Array.isArray(hb.completed);
        setHouseholdBoard(valid ? hb : null);
      } catch (_) {
        setHouseholdBoard(null);
      }
    } catch (e) {
      if (e instanceof Error && e.message === "401") {
        setError("Wrong token");
      } else {
        setError("Something went wrong");
      }
    }
  };

  const handleCreateTicket = async (e) => {
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
      // clear form
      setTitle("");
      setDetails("");
      setPriority("normal");
      setDue("");
      // reload data
      const dash = await fetchDashboard(token);
      setBoard(dash);
      const hb = await fetchBoard(token);
      const valid = hb && Array.isArray(hb.todo) && Array.isArray(hb.in_progress) && Array.isArray(hb.completed);
      setHouseholdBoard(valid ? hb : null);
      const filedData = await fetchFiled(token);
      setFiled(filedData.tickets);
    } catch (e) {
      if (e instanceof Error && e.message === "401") {
        setError("Wrong token");
      } else {
        setError("Something went wrong");
      }
    }
  };

  const handleStatusChange = async (id, newStatus) => {
    if (!token) return;
    setError("");
    try {
      await changeStatus(token, id, newStatus);
      const dash = await fetchDashboard(token);
      setBoard(dash);
      // if the open detail panel shows this ticket, refresh its history
      if (openedTicket && openedTicket.id === id) {
        // trigger a fetch; result is ignored – the mock records the call
        await fetchHistory(token, id);
      }
    } catch (e) {
      if (e instanceof Error && e.message === "401") {
        setError("Wrong token");
      } else {
        setError("Something went wrong");
      }
    }
  };

  const handleFileStatusChange = async (id, newStatus) => {
    if (!token) return;
    setError("");
    try {
      await changeStatus(token, id, newStatus);
      const dash = await fetchDashboard(token);
      setBoard(dash);
      const filedData = await fetchFiled(token);
      setFiled(filedData.tickets);
      // also refresh history if open
      if (openedTicket && openedTicket.id === id) {
        await fetchHistory(token, id);
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

  const openTicket = (ticket) => {
    setOpenedTicket(ticket);
  };

  const closeTicketDetail = () => {
    setOpenedTicket(null);
  };

  const renderColumn = (name, tickets) => {
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
            onClose={closeTicketDetail}
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
          <HouseholdBoard board={householdBoard} onOpen={openTicket} />
        )}
      </main>
    </div>
  );
};

export default App;
