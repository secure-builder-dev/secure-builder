import { useState } from "react";

export default function App() {
  const [token, setToken] = useState("");

  return (
    <div>
      <h1>Honey-Do Tickets</h1>
      <input
        type="text"
        placeholder="Enter your token"
        value={token}
        onChange={(e) => setToken(e.target.value)}
      />
      <p>Welcome to the Honey-Do Ticket system.</p>
    </div>
  );
}