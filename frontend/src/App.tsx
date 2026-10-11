import { useState } from "react";
import {
  getDashboard,
  getFiledTickets,
  createTicket as apiCreateTicket,
  changeStatus as apiChangeStatus,
} from "./api";

export default function App() {
  const [token, setToken] = useState("");
  const [dashboardData, setDashboardData] = useState<ReturnType<typeof getDashboard> | null>(null);
  const [filedTickets, setFiledTickets] = useState<ReturnType<typeof getFiledTickets> | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [title, setTitle] = useState("");
  const [details, setDetails] = useState("");
  const [priority, setPriority] = useState("normal");
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
      <h1>Honey-Do Tickets</h1>
      
      <div>
        <label htmlFor="token">Token</label>
        <input
          id="token"
          type="password"
          value={token}
          onChange={(e) => setToken(e.target.value)}
        />
        <button onClick={loadBoard}>Load</button>
      </div>

      {error && <p>{error}</p>}

      <div>
        <h2>New ticket</h2>
        <input
          label="Title"
          placeholder="Title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <textarea
          label="Details"
          placeholder="Details"
          value={details}
          onChange={(e) => setDetails(e.target.value)}
        />
        <select value={priority} onChange={(e) => setPriority(e.target.value)}>
          <option value="low">low</option>
          <option value="normal">normal</option>
          <option value="urgent">urgent</option>
        </select>
        <input
          type="date"
          label="Due"
          value={due}
          onChange={(e) => setDue(e.target.value)}
        />
        <button onClick={handleFileTicket}>File ticket</button>
      </div>

      {dashboardData && (
        <div>
          <h2>To Do</h2>
          <div>
            {dashboardData.todo.map((ticket) => (
              <div key={ticket.id} className={ticket.group === 0 ? "urgent" : ""}>
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

          <h2>In Progress</h2>
          <div>
            {dashboardData.in_progress.map((ticket) => (
              <div key={ticket.id} className={ticket.group === 0 ? "urgent" : ""}>
                <p>{ticket.title}</p>
                <p>Priority: {ticket.priority}</p>
                <p>Due: {ticket.due || "N/A"}</p>
                <button onClick={() => handleStatusChange(ticket.id, "done")}>Done</button>
              </div>
            ))}
          </div>

          <h2>Completed</h2>
          <div>
            {dashboardData.completed.map((ticket) => (
              <div key={ticket.id}>
                <p>{ticket.title}</p>
                <p>Priority: {ticket.priority}</p>
                <p>Due: {ticket.due || "N/A"}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {filedTickets && (
        <div>
          <h2>Tickets I filed</h2>
          <div>
            {filedTickets.tickets.map((ticket) => (
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
        </div>
      )}
    </div>
  );
}