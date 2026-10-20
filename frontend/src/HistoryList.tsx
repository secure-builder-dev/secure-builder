import type { TicketEvent } from "./types";

interface Props {
  events: TicketEvent[];
}

function status(s: string | null): string {
  return (s ?? "").replace(/_/g, " ");
}

function text(e: TicketEvent): string {
  if (e.kind === "filed") return `${e.actor} filed it`;
  if (e.kind === "edited") return `${e.actor} edited it`;
  return `${e.actor} moved it from ${status(e.from_status)} to ${status(e.to_status)}`;
}

export default function HistoryList({ events }: Props) {
  if (events.length === 0) {
    return <p className="empty">No history</p>;
  }
  return (
    <ol className="history" aria-label="History">
      {events.map((e) => (
        <li key={e.id}>{text(e)}</li>
      ))}
    </ol>
  );
}
