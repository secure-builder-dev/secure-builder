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
  const classes = ["summary"];
  if (overdue > 0) {
    classes.push("alert");
  }
  const text = `${overdue} overdue · ${due_today} due today · ${open} open`;
  return (
    <span className={classes.join(" ")} aria-label="Summary">
      {text}
    </span>
  );
}
