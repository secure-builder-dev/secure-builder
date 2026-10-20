id: XO-2h
unit: XO-2
state: claimed
depends_on: XO-2d
done_when: frontend/src/api.ts also exports fetchBoard(token), which sends GET /api/board like the other calls and returns the Board, throwing Error(String(status)) when the answer is not ok; frontend/src/HouseholdBoard.tsx default-exports the React component HouseholdBoard({board}) that renders <section className="panel" aria-label="Household board"> with <h2>Household board</h2> and <div className="board"> holding three <section className="column"> elements with aria-label To Do, In Progress and Completed; each column starts with <h3 className="column-title">{name} <span className="count">{number}</span></h3>, then shows one TicketCard (from TicketCard.tsx, with no children) per ticket, or <p className="empty">Nothing here</p> when it has none

# XO-2h
