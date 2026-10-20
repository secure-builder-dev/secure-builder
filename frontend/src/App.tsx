import React, { useState } from "react";
import TicketCard from "./TicketCard";
import HouseholdBoard from "./HouseholdBoard";
import Menu from "./Menu";
import Directions from "./Directions";
import TicketDetail from "./TicketDetail";
import FilterBar from "./FilterBar";
import SummaryBadge from "./SummaryBadge";
import { fetchDashboard, fetchFiled, fetchBoard, changeStatus, createTicket, fetchMe, fetchSummary } from "./api";
import type { Board, Ticket, Summary } from "./types";

export default function App() {
  const [token, setToken] = useState("");
  const [me, setMe] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [board, setBoard] = useState<Board | null>(null);
  const [houseBoard, setHouseBoard] = useState<Board | null>(null);
  const [filed, setFiled] = useState<Ticket[] | null>(null);
  const [showDirections, setShowDirections] = useState(false);
  const [openTicket, setOpenTicket] = useState<Ticket | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [boardFilter, setBoardFilter] = useState<{ q: string; priority: string; assigned_to: string }>({
    q: "",
    priority: "",
    assigned_to: "",
  });

  const openDirections = () => setShowDirections(true);
  const closeDirections = () => setShowDirections(false);

  const handleOpen = (ticket: Ticket) => {
    setOpenTicket(ticket);
  };

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
    setOpenTicket(null);
    setSummary(null);
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

      // fetch household board using current filter
      try {
        const hb = await fetchBoard(token, boardFilter);
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
      } catch {
        setSummary(null);
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
      // Preserve the currently open ticket (if any) before reloading data.
      const currentOpen = openTicket;
      // reload boards and other data (this clears openTicket temporarily)
      await handleLoad();
      // After reload, restore the open ticket with the updated status so that the detail panel stays open.
      if (currentOpen && currentOpen.id === id) {
        setOpenTicket({ ...currentOpen, status: newStatus as any });
      }
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
      // reload board and filed tickets (and summary)
      await handleLoad();
    } catch (e: any) {
      if (e instanceof Error && e.message === "401") {
        setError("Wrong token");
      } else {
        setError("Something went wrong");
      }
    }
  };

  const handleFilterApply = (filter: { q: string; priority: string; assigned_to: string }) => {
    // store filter and refetch board
    setBoardFilter(filter);
    // fetch board with new filter
    (async () => {
      try {
        const hb = await fetchBoard(token, filter);
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
        setHouseBoard(null);
      }
    })();
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
            <TicketCard key={t.id} ticket={t} onOpen={handleOpen}>
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
            <TicketCard key={t.id} ticket={t} onOpen={handleOpen}>
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
        {summary && <SummaryBadge summary={summary} />}
      </header>
      <main className="content">
        {error && <p role="alert" className="error">{error}</p>}
        {showDirections && <Directions onClose={closeDirections} />}
        {openTicket && (
          <TicketDetail
            token={token}
            ticket={openTicket}
            me={me}
            onClose={() => setOpenTicket(null)}
            onSaved={(t) => {
              // Keep the detail panel open with the updated ticket
              setOpenTicket(t);
              // Refresh boards, filed tickets, household board, and summary without clearing the open ticket
              (async () => {
                try {
                  const dash = await fetchDashboard(token);
                  setBoard(dash);
                  const f = await fetchFiled(token);
                  setFiled(f.tickets);
                  const hb = await fetchBoard(token, boardFilter);
                  setHouseBoard(hb);
                  const sum = await fetchSummary(token);
                  setSummary(sum);
                } catch (e: any) {
                  if (e instanceof Error && e.message === "401") {
                    setError("Wrong token");
                  } else {
                    setError("Something went wrong");
                  }
                }
              })();
            }}
          />
        )}
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
          <HouseholdBoard board={houseBoard} onOpen={handleOpen}>
            <FilterBar onApply={handleFilterApply} />
          </HouseholdBoard>
        )}
      </main>
    </div>
  );
}
