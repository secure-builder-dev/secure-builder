import React from "react";
import type { TicketEvent } from "./types";

interface Props {
  events: TicketEvent[];
}

function formatStatus(s: string | null): string {
  return s ? s.replace(/_/g, " ") : "";
}

export default function HistoryList({ events }: Props) {
  if (events.length === 0) {
    return <p className="empty">No history</p>;
  }

  const renderItem = (e: TicketEvent) => {
    const actor = e.actor;
    switch (e.kind) {
      case "filed":
        return `${actor} filed it`;
      case "edited":
        return `${actor} edited it`;
      case "status": {
        const from = formatStatus(e.from_status);
        const to = formatStatus(e.to_status);
        return `${actor} moved it from ${from} to ${to}`;
      }
      default:
        return "";
    }
  };

  return (
    <ol className="history" aria-label="History">
      {events.map((e) => (
        <li key={e.id}>{renderItem(e)}</li>
      ))}
    </ol>
  );
}
