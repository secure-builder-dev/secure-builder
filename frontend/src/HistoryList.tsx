import React from "react";
import type { TicketEvent } from "./types";

interface HistoryListProps {
  events: TicketEvent[];
}

export default function HistoryList({ events }: HistoryListProps) {
  const renderEvent = (e: TicketEvent) => {
    switch (e.kind) {
      case "filed":
        return `${e.actor} filed it`;
      case "status":
        const from = e.from_status?.replace("_", " ") ?? "";
        const to = e.to_status?.replace("_", " ") ?? "";
        return `${e.actor} moved it from ${from} to ${to}`;
      case "edited":
        return `${e.actor} edited it`;
      default:
        return "";
    }
  };

  return (
    <>{events.length > 0 ? (
      <ol className="history" aria-label="History">
        {events.map((ev) => (
          <li key={ev.id}>{renderEvent(ev)}</li>
        ))}
      </ol>
    ) : (
      <p className="empty">No history</p>
    )}</>
  );
}
