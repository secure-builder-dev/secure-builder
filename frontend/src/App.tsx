import { useState } from 'react';

const App = () => {
  const [token, setToken] = useState('');

  return (
    <div>
      <h1>Honey-Do Tickets</h1>
      <div>
        <label>
          Token:
          <input
            type="text"
            value={token}
            onChange={(e) => setToken(e.target.value)}
          />
        </label>
      </div>
      <div>
        <h2>New Ticket</h2>
        <form>
          <input type="text" placeholder="Title" />
          <textarea placeholder="Details" />
          <select>
            <option value="low">Low</option>
            <option value="normal" selected>
              Normal
            </option>
            <option value="urgent">Urgent</option>
          </select>
          <input type="date" />
          <button type="submit">Create</button>
        </form>
      </div>
      <div>
        <h2>Board</h2>
        <div>
          <h3>To Do</h3>
        </div>
        <div>
          <h3>In Progress</h3>
        </div>
        <div>
          <h3>Completed</h3>
        </div>
      </div>
      <div>
        <h2>Tickets I Filed</h2>
      </div>
    </div>
  );
};

export default App;