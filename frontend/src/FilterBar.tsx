import { FormEvent } from "react";

interface FilterBarProps {
  onApply: (filter: { q: string; priority: string; assigned_to: string }) => void;
}

export default function FilterBar({ onApply }: FilterBarProps) {
  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = e.currentTarget;
    const formData = new FormData(form);
    const q = (formData.get("q") as string).trim();
    const priority = formData.get("priority") as string;
    const assigned_to = formData.get("assigned_to") as string;

    onApply({
      q: q || "",
      priority: priority || "",
      assigned_to: assigned_to || "",
    });
  };

  return (
    <form className="filter-bar" role="search" aria-label="Filter household board" onSubmit={handleSubmit}>
      <label htmlFor="filter-q">Search</label>
      <input id="filter-q" name="q" type="text" />

      <label htmlFor="filter-priority">Priority</label>
      <select id="filter-priority" name="priority">
        <option value="">Any</option>
        <option value="low">low</option>
        <option value="normal">normal</option>
        <option value="urgent">urgent</option>
      </select>

      <label htmlFor="filter-assigned-to">Assigned to</label>
      <select id="filter-assigned-to" name="assigned_to">
        <option value="">Anyone</option>
        <option value="her">her</option>
        <option value="him">him</option>
      </select>

      <button type="submit">Apply</button>
    </form>
  );
}