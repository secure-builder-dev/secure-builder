id: XO-3f
unit: XO-3
state: claimed
depends_on: -
done_when: TicketCard takes an optional prop onOpen(ticket): with it the article also has the class openable, a click on the h3.card-title calls onOpen with the ticket, and the Enter key pressed while the title's span.hover-target has focus calls it too; without onOpen a TicketCard renders exactly as before (no openable class, nothing happens on a click), and with onOpen it gets no new button; HouseholdBoard takes the optional props onOpen, passed to every card it shows, and children, rendered between its h2 and its div.board

# XO-3f
