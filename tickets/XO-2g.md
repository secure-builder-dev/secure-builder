id: XO-2g
unit: XO-2
state: in review
depends_on: XO-2f
done_when: once loaded, main shows, after My board, <section className="panel" aria-label="Tickets I filed"> with <h2>Tickets I filed</h2> and <div className="card-list"> holding one TicketCard per ticket of /api/filed, in that order, so a newly filed ticket lands on a card of its own after the reload; a filed ticket with status done gets a Close and a Reopen button as its TicketCard's children — other filed tickets get none; Close and Reopen call changeStatus with closed and open and then reload (dashboard and filed tickets)

# XO-2g
