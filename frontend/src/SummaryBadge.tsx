import React from "react";

type Summary = {
  overdue: number;
  due_today: number;
  open: number;
};

type Props = {
  summary: Summary;
};

export default function SummaryBadge({ summary }: Props) {
  const { overdue, due_today, open } = summary;
  const className = overdue > 0 ? "summary alert" : "summary";
  return (
    <span className={className} aria-label="Summary">
      {overdue} overdue · {due_today} due today · {open} open
    </span>
  );
}
