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

  // Filter out any events that render to an empty string (unknown kinds)
  const rendered = events.map(renderEvent);
  const hasContent = rendered.some((text) => text !== "");

  return (
    <>{hasContent ? (
      <ol className="history" aria-label="History">
        {events.map((ev, idx) => {
          const text = renderEvent(ev);
          if (!text) return null;
          return <li key={ev.id}>{text}</li>;
        })}
      </ol>
    ) : (
      <p className="empty">No history</p>
    )}</>
  );
}
