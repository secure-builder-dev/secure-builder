import type { Board } from "./types";
import TicketCard from "./TicketCard";

interface HouseholdBoardProps {
  board: Board;
}

const COLUMNS: Array<{ name: string; key: keyof Board }> = [
  { name: "To Do", key: "todo" },
  { name: "In Progress", key: "in_progress" },
  { name: "Completed", key: "completed" },
];

export default function HouseholdBoard({ board }: HouseholdBoardProps) {
  return (
    <section className="panel" aria-label="Household board">
      <h2>Household board</h2>
      <div className="board">
        {COLUMNS.map(({ name, key }) => {
          const tickets = board[key];
          return (
            <section className="column" aria-label={name} key={key}>
              <h3 className="column-title">
                {name} <span className="count">{tickets.length}</span>
              </h3>
              {tickets.length === 0 ? (
                <p className="empty">Nothing here</p>
              ) : (
                tickets.map((t) => <TicketCard key={t.id} ticket={t} />)
              )}
            </section>
          );
        })}
      </div>
    </section>
  );
}