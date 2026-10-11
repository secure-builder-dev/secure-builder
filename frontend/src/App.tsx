import { useState } from "react";
import "./styles.css";
import {
  getDashboard,
  getFiledTickets,
  createTicket as apiCreateTicket,
  changeStatus as apiChangeStatus,
} from "./api";
import type { DashboardData, FiledTicketsData } from "./api";

export default function App() {
  const [token, setToken] = useState("");
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [filedTickets, setFiledTickets] = useState<FiledTicketsData | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [title, setTitle] = useState("");
  const [details, setDetails] = useState("");
  const [priority, setPriority] = useState<"low" | "normal" | "urgent">("normal");
  const [due, setDue] = useState("");

  const loadBoard = async () => {
    setError(null);
    try {
      const [dash, filed] = await Promise.all([
        getDashboard(token),
        getFiledTickets(token),
      ]);
      setDashboardData(dash);
      setFiledTickets(filed);
    } catch (err: any) {
      if (err.status === 401) {
        setError("Wrong token");
      } else {
        setError("Something went wrong");
      }
    }
  };

  const handleFileTicket = async () => {
    if (!title.trim()) return;
    try {
      await apiCreateTicket(token, { title: title.trim(), details, priority, due: due || null });
      setTitle("");
      setDetails("");
      setPriority("normal");
      setDue("");
      await loadBoard();
    } catch (err: any) {
      if (err.status === 401) {
        setError("Wrong token");
      } else {
        setError("Something went wrong");
      }
    }
  };

  const handleStatusChange = async (ticketId: number, newStatus: string) => {
    try {
      await apiChangeStatus(token, ticketId, newStatus);
      await loadBoard();
    } catch (err: any) {
      if (err.status === 401) {
        setError("Wrong token");
      } else {
        setError("Something went wrong");
      }
    }
  };

  return (
    <div>
      <header className="topbar">
        <h1 className="brand">~/honey-do</h1>
        <div>
          <label htmlFor="token">Token</label>
          <input
            id="token"
            type="password"
            value={token}
            onChange={(e) => setToken(e.target.value)}
          />
          <button onClick={loadBoard} aria-label="Load">Load</button>
        </div>
      </header>

      {error && <p>{error}</p>}

      <fieldset>
        <legend>New ticket</legend>
        <label htmlFor="title">Title</label>
        <input
          id="title"
          aria-label="Title"
          placeholder="Title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <label htmlFor="details">Details</label>
        <textarea
          id="details"
          aria-label="Details"
          placeholder="Details"
          value={details}
          onChange={(e) => setDetails(e.target.value)}
        />
        <label htmlFor="priority">Priority</label>
        <select id="priority" aria-label="Priority" value={priority} onChange={(e) => setPriority(e.target.value as "low" | "normal" | "urgent")}>
          <option value="low">low</option>
          <option value="normal">normal</option>
          <option value="urgent">urgent</option>
        </select>
        <label htmlFor="due">Due</label>
        <input
          id="due"
          aria-label="Due"
          type="date"
          value={due}
          onChange={(e) => setDue(e.target.value)}
        />
        <button onClick={handleFileTicket} aria-label="File ticket">File ticket</button>
      </fieldset>

      {dashboardData && (
        <section className="board">
          <div className="column">
            <h2 id="todo-heading" role="heading">To Do</h2>
            {dashboardData.todo?.map((ticket: any) => (
              <div key={ticket.id} className={`card ${ticket.group === 0 ? "urgent" : ""}`}>
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
            <h2 id="in-progress-heading" role="heading">In Progress</h2>
            {dashboardData.in_progress?.map((ticket: any) => (
              <div key={ticket.id} className={`card ${ticket.group === 0 ? "urgent" : ""}`}>
                <p>{ticket.title}</p>
                <p>Priority: {ticket.priority}</p>
                <p>Due: {ticket.due || "N/A"}</p>
                <button onClick={() => handleStatusChange(ticket.id, "done")}>Done</button>
              </div>
            ))}
          </div>

          <div className="column">
            <h2 id="completed-heading" role="heading">Completed</h2>
            {dashboardData.completed?.map((ticket: any) => (
              <div key={ticket.id} className="card">
                <p>{ticket.title}</p>
                <p>Priority: {ticket.priority}</p>
                <p>Due: {ticket.due || "N/A"}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {filedTickets && (
        <section>
          <h2 id="filed-heading" role="heading">Tickets I filed</h2>
          <div>
            {filedTickets.tickets?.map((ticket: any) => (
              <div key={ticket.id}>
                <p>{ticket.title}</p>
                <p>Priority: {ticket.priority}</p>
                <p>Due: {ticket.due || "N/A"}</p>
                {ticket.status === "done" && (
                  <>
                    <button onClick={() => handleStatusChange(ticket.id, "closed")}>Close</button>
                    <button onClick={() => handleStatusChange(ticket.id, "open")}>Reopen</button>
                  </>
                )}
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}