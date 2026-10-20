import React, { useState, FormEvent } from "react";
import type { Ticket, Priority } from "./types";

interface Props {
  ticket: Ticket;
  onSave: (changes: { title: string; details: string; priority: Priority; due: string | null }) => void;
  onCancel: () => void;
  error?: string;
}

export default function EditTicketForm({ ticket, onSave, onCancel, error }: Props) {
  const [title, setTitle] = useState(ticket.title);
  const [details, setDetails] = useState(ticket.details);
  const [priority, setPriority] = useState<Priority>(ticket.priority);

  const [due, setDue] = useState(ticket.due ?? "");

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const dueValue = due === "" ? null : due;
    onSave({ title, details, priority, due: dueValue });
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
