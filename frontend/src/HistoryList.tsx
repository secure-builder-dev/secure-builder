import type { TicketEvent } from "./types";

interface HistoryListProps {
  events: TicketEvent[];
}

export default function HistoryList({ events }: HistoryListProps) {
  const formatStatus = (s: string | null) => {
    if (!s) return "";
    return s.replace(/_/g, " ");
  };

  const renderItem = (e: TicketEvent) => {
    switch (e.kind) {
      case "filed":
        return `${e.actor} filed it`;
      case "status":
        return `${e.actor} moved it from ${formatStatus(e.from_status)} to ${formatStatus(e.to_status)}`;
      case "edited":
        return `${e.actor} edited it`;
      default:
        return "";
    }
  };

  if (events.length === 0) {
    return <p className="empty">No history</p>;
  }

  return (
    <ol className="history" aria-label="History">
      {events.map((e) => (
        <li key={e.id}>{renderItem(e)}</li>
      ))}
    </ol>
  );
}
