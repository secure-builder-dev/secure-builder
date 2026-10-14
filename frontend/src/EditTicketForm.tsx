import type { Ticket } from "./types";

interface EditTicketFormProps {
  ticket: Ticket;
  onSave: (changes: { title: string; details: string; priority: "low" | "normal" | "urgent"; due: string | null }) => void;
  onCancel: () => void;
  error?: string;
}

export default function EditTicketForm({ ticket, onSave, onCancel, error }: EditTicketFormProps) {
  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const title = formData.get("title") as string;
    const details = formData.get("details") as string;
    const priority = formData.get("priority") as "low" | "normal" | "urgent";
    const dueRaw = formData.get("due") as string;
    const due = dueRaw === "" ? null : dueRaw;
    onSave({ title, details, priority, due });
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
        <input name="title" defaultValue={ticket.title} />
      </label>
      <label>
        Details
        <textarea name="details" defaultValue={ticket.details} />
      </label>
      <label>
        Priority
        <select name="priority" defaultValue={ticket.priority}>
          <option value="low">low</option>
          <option value="normal">normal</option>
          <option value="urgent">urgent</option>
        </select>
      </label>
      <label>
        Due
        <input name="due" type="date" defaultValue={ticket.due || ""} />
      </label>
      <button type="submit">Save</button>
      <button type="button" onClick={onCancel}>Cancel</button>
    </form>
  );
}
