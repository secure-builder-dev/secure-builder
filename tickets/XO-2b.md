id: XO-2b
unit: XO-2
state: claimed
depends_on: -
done_when: frontend/src/TicketCard.tsx default-exports the React component TicketCard({ticket, children}) (children optional) that renders <article className="card" aria-label={ticket.title}>, with the classes "card urgent" when ticket.group is 0; inside the article: <h3 className="card-title"> holding the title, then <div className="card-meta"> holding <span className={`badge priority-${priority}`}> (the priority), <span className="due">due {due}</span> only when due is set, <span className={`pill status-${status}`}> (the status with '_' shown as a space, e.g. in progress) and <span className="who">for {assigned_to}</span>; when children are given they are rendered inside <div className="card-actions"> after the meta row — with no children (undefined, null or false) there is no card-actions element; all ticket text is rendered as React text, never as HTML

# XO-2b
