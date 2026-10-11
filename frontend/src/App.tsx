import { useState } from "react";
import { 
  getDashboardAndFiled,
  createTicket as apiCreateTicket,
  changeStatus as apiChangeStatus,
  fetchMe,
} from "./api";
import HoverCard from "./HoverCard";
import Menu from "./Menu";
import Directions from "./Directions";
import "./styles.css";

type DashboardData = {
  todo: Array<{ id: number; title: string; details: string; priority: string; due: string | null; status: string; filed_by: string; assigned_to: string; created_at: string; group: number }>;
  in_progress: Array<{ id: number; title: string; details: string; priority: string; due: string | null; status: string; filed_by: string; assigned_to: string; created_at: string; group: number }>;
  completed: Array<{ id: number; title: string; details: string; priority: string; due: string | null; status: string; filed_by: string; assigned_to: string; created_at: string }>;
};

type FiledData = {
  tickets: Array<{ id: number; title: string; details: string; priority: string; due: string | null; status: string; filed_by: string; assigned_to: string; created_at: string }>;
};

export default function App() {
  const [token, setToken] = useState("");
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [filedData, setFiledData] = useState<FiledData | null>(null);
  const [currentUser, setCurrentUser] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const [newTitle, setNewTitle] = useState("");
  const [newDetails, setNewDetails] = useState("");
  const [newPriority, setNewPriority] = useState("normal");
  const [newDue, setNewDue] = useState("");

  const [showDirections, setShowDirections] = useState(false);

  const loadBoard = async () => {
    setLoading(true);
    setError(null);
    setCurrentUser(null);
    try {
      const [result, meResult] = await Promise.allSettled([
        getDashboardAndFiled(token),
        fetchMe(token)
      ]);
      
      if (result.status === 'fulfilled') {
        setDashboardData(result.value.dashboard);
        setFiledData(result.value.filed);
      } else if (result.status === 'rejected') {
        const err = result.reason as Error;
        if (err.message === "WRONG_TOKEN") {
          setError("Wrong token");
        } else {
          setError("Something went wrong");
        }
      }
      
      if (meResult.status === 'fulfilled') {
        const meData = await meResult.value;
        if (meData && meData.user) {
          setCurrentUser(meData.user);
        }
      }
    } catch (e: unknown) {
      const err = e as Error;
      if (err.message === "WRONG_TOKEN") {
        setError("Wrong token");
      } else {
        setError("Something went wrong");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleFileTicket = async () => {
    setError(null);
    try {
      await apiCreateTicket(token, {
        title: newTitle,
        details: newDetails,
        priority: newPriority,
        due: newDue || null,
      });
      setNewTitle("");
      setNewDetails("");
      setNewPriority("normal");
      setNewDue("");
      await loadBoard();
    } catch (e: unknown) {
      const err = e as Error;
      if (err.message === "WRONG_TOKEN") {
        setError("Wrong token");
      } else {
        setError("Something went wrong");
      }
    }
  };

  const handleStatusChange = async (ticketId: number, status: string) => {
    setError(null);
    try {
      await apiChangeStatus(token, ticketId, status);
      await loadBoard();
    } catch (e: unknown) {
      const err = e as Error;
      if (err.message === "WRONG_TOKEN") {
        setError("Wrong token");
      } else {
        setError("Something went wrong");
      }
    }
  };

  return (
    <div>
      <div className="topbar">
        <h1 className="brand">~/honey-do</h1>
        <Menu onDirections={() => setShowDirections(true)} />
        <label htmlFor="token-input">Token</label>
        <input
          id="token-input"
          type="password"
          value={token}
          onChange={(e) => setToken(e.target.value)}
        />
        <button onClick={loadBoard} aria-label="Load" disabled={loading}>Load</button>
      </div>

      {error && <p className="error">{error}</p>}
      
      {currentUser && <p>Signed in as {currentUser}</p>}

      {showDirections && (
        <Directions onClose={() => setShowDirections(false)} />
      )}

      <fieldset>
        <legend>New Ticket{currentUser ? ` for ${currentUser === 'her' ? 'him' : 'her'}` : ''}</legend>
        <div>
          <label htmlFor="title-input">Title:</label>
          <input
            id="title-input"
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
          />
        </div>
        <div>
          <label htmlFor="details-input">Details:</label>
          <textarea
            id="details-input"
            value={newDetails}
            onChange={(e) => setNewDetails(e.target.value)}
          />
        </div>
        <div>
          <label htmlFor="priority-select">Priority:</label>
          <select
            id="priority-select"
            value={newPriority}
            onChange={(e) => setNewPriority(e.target.value)}
          >
            <option value="low">low</option>
            <option value="normal">normal</option>
            <option value="urgent">urgent</option>
          </select>
        </div>
        <div>
          <label htmlFor="due-input">Due:</label>
          <input
            id="due-input"
            type="date"
            value={newDue}
            onChange={(e) => setNewDue(e.target.value)}
          />
        </div>
        <button type="button" onClick={handleFileTicket} aria-label="File ticket">File ticket</button>
      </fieldset>

      {dashboardData && (
        <div className="board" role="main">
          <div className="column">
            <h3>To Do</h3>
            {dashboardData.todo.map((ticket) => (
              <div key={ticket.id} className={`card${ticket.group === 0 ? " urgent" : ""}`}>
                <p><HoverCard ticket={ticket}>{ticket.title}</HoverCard></p>
                <p>Priority: {ticket.priority}</p>
                <p>Due: {ticket.due || "N/A"}</p>
                {ticket.status === "open" && (
                  <button onClick={() => handleStatusChange(ticket.id, "acknowledged")}>
                    Acknowledge
                  </button>
                )}
                {ticket.status === "acknowledged" && (
                  <button onClick={() => handleStatusChange(ticket.id, "in_progress")}>
                    Start
                  </button>
                )}
              </div>
            ))}
          </div>
          <div className="column">
            <h3>In Progress</h3>
            {dashboardData?.in_progress && dashboardData.in_progress.map((ticket) => (
              <div key={ticket.id} className={`card${ticket.group === 0 ? " urgent" : ""}`}>
                <p><HoverCard ticket={ticket}>{ticket.title}</HoverCard></p>
                <p>Priority: {ticket.priority}</p>
                <p>Due: {ticket.due || "N/A"}</p>
                <button onClick={() => handleStatusChange(ticket.id, "done")}>
                  Done
                </button>
              </div>
            ))}
          </div>
          <div className="column">
            <h3>Completed</h3>
            {dashboardData?.completed && dashboardData.completed.map((ticket) => (
              <div key={ticket.id} className="card">
                <p><HoverCard ticket={ticket}>{ticket.title}</HoverCard></p>
                <p>Priority: {ticket.priority}</p>
                <p>Due: {ticket.due || "N/A"}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {filedData && (
        <div>
          <h2>Tickets I Filed</h2>
          {filedData.tickets?.map((ticket) => (
            <div key={ticket.id}>
              <p>{ticket.title}</p>
              <p>Priority: {ticket.priority}</p>
              <p>Due: {ticket.due || "N/A"}</p>
              <p>Status: {ticket.status}</p>
              {ticket.status === "done" && (
                <>
                  <button onClick={() => handleStatusChange(ticket.id, "closed")}>
                    Close
                  </button>
                  <button onClick={() => handleStatusChange(ticket.id, "open")}>
                    Reopen
                  </button>
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}


