import { useState } from "react";
import type { Board, NewTicket, Status, Ticket, Me, User, BoardFilter, Summary } from "./types";
import { changeStatus, createTicket, fetchDashboard, fetchFiled, fetchBoard, fetchMe, fetchSummary } from "./api";
import TicketCard from "./TicketCard";
import HouseholdBoard from "./HouseholdBoard";
import Menu from "./Menu";
import Directions from "./Directions";
import TicketDetail from "./TicketDetail";
import FilterBar from "./FilterBar";
import SummaryBadge from "./SummaryBadge";
import "./styles.css";

export default function App() {
  const [token, setToken] = useState("");
  const [dashboard, setDashboard] = useState<Board | null>(null);
  const [filed, setFiled] = useState<Ticket[]>([]);
  const [householdBoard, setHouseholdBoard] = useState<Board | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [boardError, setBoardError] = useState<boolean>(false);
  const [me, setMe] = useState<User | null>(null);
  const [title, setTitle] = useState("");
  const [details, setDetails] = useState("");
  const [priority, setPriority] = useState<"low" | "normal" | "urgent">("normal");
  const [due, setDue] = useState("");
  const [showDirections, setShowDirections] = useState(false);
  const [openTicket, setOpenTicket] = useState<Ticket | null>(null);
  const [detailKey, setDetailKey] = useState(0);
  const [boardFilter, setBoardFilter] = useState<BoardFilter>({ q: "", priority: "", assigned_to: "" });
  const [summary, setSummary] = useState<Summary | null>(null);

  async function handleLoad() {
    setError(null);
    setTitle("");
    setDetails("");
    setPriority("normal");
    setDue("");
    setBoardError(false);
    setMe(null);
    setOpenTicket(null);
    setSummary(null);
    try {
      const dash = await fetchDashboard(token);
      const filedRes = await fetchFiled(token).catch(() => undefined);
      const boardRes = await fetchBoard(token, boardFilter).catch((e) => {
        if (e instanceof Error && e.message !== "401") {
          setBoardError(true);
        }
        return undefined;
      });
      const meRes = await fetchMe(token).catch(() => undefined);
      const summaryRes = await fetchSummary(token).catch(() => undefined);
      
      setDashboard(dash);
      setFiled(filedRes?.tickets ?? []);
      
      // Validate board response structure
      if (boardRes && typeof boardRes === "object" && 
          Array.isArray(boardRes.todo) && 
          Array.isArray(boardRes.in_progress) && 
          Array.isArray(boardRes.completed)) {
        setHouseholdBoard(boardRes);
      } else {
        setBoardError(true);
        setHouseholdBoard(null);
      }
      
      // Validate me response
      if (meRes && typeof meRes === "object" && 
          (meRes.user === "her" || meRes.user === "him")) {
        setMe(meRes.user);
      }
      
      // Validate summary response
      if (summaryRes && typeof summaryRes === "object" &&
          typeof summaryRes.overdue === "number" &&
          typeof summaryRes.due_today === "number" &&
          typeof summaryRes.open === "number") {
        setSummary(summaryRes);
      }
    } catch (e) {
      if (e instanceof Error && e.message === "401") {
        setError("Wrong token");
      } else {
        setError("Something went wrong");
      }
      setDashboard(null);
      setFiled([]);
      setHouseholdBoard(null);
    }
  }

  async function handleFileTicket() {
    if (!title.trim()) return;
    setError(null);
    try {
      await createTicket(token, {
        title: title.trim(),
        details,
        priority,
        due: due || null,
      });
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

  async function handleStatusChange(id: number, status: Status) {
    setError(null);
    try {
      await changeStatus(token, id, status);
      setDetailKey((n) => n + 1);
      // Force a re-render of TicketDetail by updating the key before handleLoad
      // This ensures history is refetched when the panel remounts
      await new Promise(resolve => setTimeout(resolve, 0));
      await handleLoad();
    } catch (e) {
      if (e instanceof Error && e.message === "401") {
        setError("Wrong token");
      } else {
        setError("Something went wrong");
      }
    }
  }

  function handleFilterApply(filter: BoardFilter) {
    setBoardFilter(filter);
    // Re-fetch the household board with the new filter
    fetchBoard(token, filter)
      .then((boardRes) => {
        if (boardRes && typeof boardRes === "object" &&
            Array.isArray(boardRes.todo) &&
            Array.isArray(boardRes.in_progress) &&
            Array.isArray(boardRes.completed)) {
          setHouseholdBoard(boardRes);
        }
      })
      .catch(() => {
        // Silently fail - keep existing board
      });
  }

  function renderColumn(name: string, ariaLabel: string, tickets: Ticket[]) {
    const cards = tickets.map((t) => {
      let children: React.ReactNode;
      if (t.status === "open") {
        children = (
          <button onClick={() => handleStatusChange(t.id, "acknowledged")}>
            Acknowledge
          </button>
        );
      } else if (t.status === "acknowledged") {
        children = (
          <button onClick={() => handleStatusChange(t.id, "in_progress")}>
            Start
          </button>
        );
      } else if (t.status === "in_progress") {
        children = (
          <button onClick={() => handleStatusChange(t.id, "done")}>Done</button>
        );
      }
      return (
        <TicketCard
          key={t.id}
          ticket={t}
          onOpen={(ticket) => setOpenTicket(ticket)}
        >{children}</TicketCard>
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
          cards
        )}
      </section>
    );
  }

  return (
    <div className="app">
      <header className="topbar">
        <h1 className="brand">~/honey-do</h1>
        <Menu onDirections={() => setShowDirections(true)} />
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
        {me && <span className="whoami">Signed in as {me}</span>}
        {summary && <SummaryBadge summary={summary} />}
      </header>
      <main className="content">
        {error && <p role="alert" className="error">{error}</p>}
        {showDirections && <Directions onClose={() => setShowDirections(false)} />}
        {openTicket && (
          <TicketDetail
            key={`${openTicket.id}-${detailKey}`}
            token={token}
            ticket={openTicket}
            me={me}
            onClose={() => setOpenTicket(null)}
            onSaved={(updated) => {
              setOpenTicket(updated);
              handleLoad();
            }}
          />
        )}
        <section className="panel new-ticket" aria-label="New ticket">
          <h2>{me === "her" ? "New ticket for him" : me === "him" ? "New ticket for her" : "New ticket"}</h2>
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
                onChange={(e) =>
                  setPriority(e.target.value as "low" | "normal" | "urgent")
                }
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
        {dashboard && (
          <section className="panel" aria-label="My board">
            <h2>My board</h2>
            <div className="board">
              {renderColumn("To Do", "To Do", dashboard.todo)}
              {renderColumn("In Progress", "In Progress", dashboard.in_progress)}
              {renderColumn("Completed", "Completed", dashboard.completed)}
            </div>
          </section>
        )}
        {dashboard && (
          <section className="panel" aria-label="Tickets I filed">
            <h2>Tickets I filed</h2>
            <div className="card-list">
              {filed.length === 0 ? (
                <p className="empty">Nothing here</p>
              ) : (
                filed.map((t) => {
                  let children: React.ReactNode;
                  if (t.status === "done") {
                    children = (
                      <>
                        <button onClick={() => handleStatusChange(t.id, "closed")}>
                          Close
                        </button>
                        <button onClick={() => handleStatusChange(t.id, "open")}>
                          Reopen
                        </button>
                      </>
                    );
                  }
                  return (
                    <TicketCard
                      key={t.id}
                      ticket={t}
                      onOpen={(ticket) => setOpenTicket(ticket)}
                    >{children}</TicketCard>
                  );
                })
              )}
            </div>
          </section>
        )}
        {!boardError && householdBoard && (
          <HouseholdBoard
            board={householdBoard}
            onOpen={(ticket) => setOpenTicket(ticket)}
          >
            <FilterBar onApply={handleFilterApply} />
          </HouseholdBoard>
        )}
      </main>
    </div>
  );
}
