import { Summary } from "./types";

interface SummaryBadgeProps {
  summary: Summary;
}

export default function SummaryBadge({ summary }: SummaryBadgeProps) {
  const { overdue, due_today, open } = summary;
  const text = `${overdue} overdue \u00b7 ${due_today} due today \u00b7 ${open} open`;
  const className = `summary${overdue > 0 ? " alert" : ""}`;

  return (
    <span role="status" className={className} aria-label="Summary">
      {text}
    </span>
  );
}