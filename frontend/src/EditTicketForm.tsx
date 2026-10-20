import { useState } from "react";
import type { Priority, Ticket, TicketEdit } from "./types";

interface Props {
  ticket: Ticket;
  onSave(changes: TicketEdit): void;
  onCancel(): void;
  error?: string;
}

export default function EditTicketForm({ ticket, onSave, onCancel, error }: Props) {
  const [title, setTitle] = useState(ticket.title);
  const [details, setDetails] = useState(ticket.details);
  const [priority, setPriority] = useState<Priority>(ticket.priority);
  const [due, setDue] = useState(ticket.due ?? "");

  function submit(e: React.FormEvent) {
    e.preventDefault();
    onSave({ title, details, priority, due: due === "" ? null : due });
  }

  return (
    <form className="edit-ticket" aria-label="Edit ticket" onSubmit={submit}>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <label>
        Title
        <input type="text" value={title} onChange={(e) => setTitle(e.target.value)} />
      </label>
      <label>
        Details
        <textarea value={details} onChange={(e) => setDetails(e.target.value)} />
      </label>
      <label>
        Priority
        <select value={priority} onChange={(e) => setPriority(e.target.value as Priority)}>
          <option value="low">low</option>
          <option value="normal">normal</option>
          <option value="urgent">urgent</option>
        </select>
      </label>
      <label>
        Due
        <input type="date" value={due} onChange={(e) => setDue(e.target.value)} />
      </label>
      <button type="submit">Save</button>
      <button type="button" onClick={onCancel}>Cancel</button>
    </form>
  );
}