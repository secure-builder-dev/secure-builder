import { useState } from "react";
import { 
  getDashboardAndFiled,
  createTicket as apiCreateTicket,
  changeStatus as apiChangeStatus,
} from "./api";
import "./styles.css";

type DashboardData = {
  todo: Array<{ id: number; title: string; priority: string; due: string | null; status: string; group: number }>;
  in_progress: Array<{ id: number; title: string; priority: string; due: string | null; status: string; group: number }>;
  completed: Array<{ id: number; title: string; priority: string; due: string | null; status: string }>;
};

type FiledData = {
  tickets: Array<{ id: number; title: string; priority: string; due: string | null; status: string }>;
};

export default function App() {
  const [token, setToken] = useState("");
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [filedData, setFiledData] = useState<FiledData | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [newTitle, setNewTitle] = useState("");
  const [newDetails, setNewDetails] = useState("");
  const [newPriority, setNewPriority] = useState("normal");
  const [newDue, setNewDue] = useState("");

  const loadBoard = async () => {
    setError(null);
    try {
      const result = await getDashboardAndFiled(token);
      setDashboardData(result.dashboard);
      setFiledData(result.filed);
    } catch (e: unknown) {
      const err = e as Error;
      if (err.message === "WRONG_TOKEN") {
        setError("Wrong token");
      } else {
        setError("Something went wrong");
      }
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
        <label htmlFor="token-input">Token</label>
        <input
          id="token-input"
          type="password"
          value={token}
          onChange={(e) => setToken(e.target.value)}
        />
        <button onClick={loadBoard} aria-label="Load">Load</button>
      </div>

      {error && <p>{error}</p>}



      <fieldset>
        <legend>New ticket</legend>
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
                <p>{ticket.title}</p>
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
                <p>{ticket.title}</p>
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
                <p>{ticket.title}</p>
                <p>Priority: {ticket.priority}</p>
                <p>Due: {ticket.due || "N/A"}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {filedData?.tickets && (
        <div>
          <h2>Tickets I filed</h2>
          {filedData.tickets.map((ticket) => (
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


