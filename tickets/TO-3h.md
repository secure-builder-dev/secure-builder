id: TO-3h
unit: TO-3
state: in review
depends_on: TO-3e, TO-3g
done_when: TicketDetail (default export of frontend/src/TicketDetail.tsx, props token, ticket, me, onClose and optional onSaved) renders section.panel.ticket-detail named Ticket details with an h2 holding the title, p.detail-text with the details (only when they are not empty), a div.card-meta with the same spans as TicketCard, a Comments h3 with CommentThread, a History h3 with HistoryList, and a Close details button (class close-detail) that calls onClose; it fetches the ticket's comments and history with the token when it opens and again whenever ticket.id changes, and a failed or malformed answer leaves that list empty while the rest of the panel works; adding a comment POSTs it and then shows the answered comment at the end of the list, and a failed POST shows p.error with role alert reading Could not add the comment inside the panel and adds nothing

# TO-3h
