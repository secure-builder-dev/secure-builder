import React, { useState, FormEvent, ChangeEvent } from "react";

type Filter = {
  q: string;
  priority: string;
  assigned_to: string;
};

type Props = {
  onApply: (filter: Filter) => void;
};

export default function FilterBar({ onApply }: Props) {
  const [q, setQ] = useState("");
  const [priority, setPriority] = useState("");
  const [assignedTo, setAssignedTo] = useState("");

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    onApply({ q: q.trim(), priority, assigned_to: assignedTo });
  };

  const handleQChange = (e: ChangeEvent<HTMLInputElement>) => setQ(e.target.value);
  const handlePriorityChange = (e: ChangeEvent<HTMLSelectElement>) => setPriority(e.target.value);
  const handleAssignedChange = (e: ChangeEvent<HTMLSelectElement>) => setAssignedTo(e.target.value);

  return (
    <form
      className="filter-bar"
      role="search"
      aria-label="Filter household board"
      onSubmit={handleSubmit}
    >
      <label>
        Search
        <input type="text" value={q} onChange={handleQChange} />
      </label>
      <label>
        Priority
        <select value={priority} onChange={handlePriorityChange}>
          <option value="">Any</option>
          <option value="low">low</option>
          <option value="normal">normal</option>
          <option value="urgent">urgent</option>
        </select>
      </label>
      <label>
        Assigned to
        <select value={assignedTo} onChange={handleAssignedChange}>
          <option value="">Anyone</option>
          <option value="her">her</option>
          <option value="him">him</option>
        </select>
      </label>
      <button type="submit">Apply</button>
    </form>
  );
}
