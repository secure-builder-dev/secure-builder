import type { Summary } from "./types";

interface Props {
  summary: Summary;
}

export default function SummaryBadge({ summary }: Props) {
  const cls = summary.overdue > 0 ? "summary alert" : "summary";
  return (
    <span className={cls} aria-label="Summary">
      {summary.overdue} overdue · {summary.due_today} due today · {summary.open} open
    </span>
  );
}
