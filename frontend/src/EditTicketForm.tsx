import React, { useState, FormEvent } from "react";
import type { Ticket, TicketEdit } from "./types";

interface EditTicketFormProps {
  ticket: Ticket;
  onSave: (changes: TicketEdit) => void;
  onCancel: () => void;
  error?: string;
}

export default function EditTicketForm({ ticket, onSave, onCancel, error }: EditTicketFormProps) {
  const [title, setTitle] = useState(ticket.title);
  const [details, setDetails] = useState(ticket.details);
  const [priority, setPriority] = useState(ticket.priority);
  const [due, setDue] = useState(ticket.due ?? ""); // empty string for null

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const changes: TicketEdit = {
      title,
      details,
      priority,
      due: due === "" ? null : due,
    };
    onSave(changes);
  };

  return (
    <form className="edit-ticket" aria-label="Edit ticket" onSubmit={handleSubmit}>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
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
        <select value={priority} onChange={(e) => setPriority(e.target.value as any)}>
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
      <button type="submit">Save</button>
      <button type="button" onClick={onCancel}>
        Cancel
      </button>
    </form>
  );
}
