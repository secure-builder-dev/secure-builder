id: TO-3a
unit: TO-3
state: open
depends_on: -
done_when: backend/app/models.py also defines Comment (table comments) with exactly the columns id (Integer primary key), ticket_id (Integer, ForeignKey('tickets.id')), author (String), body (String(500)) and created_at (DateTime(timezone=True)); models.py also defines TicketEvent (table ticket_events) with exactly the columns id (Integer primary key), ticket_id (Integer, ForeignKey('tickets.id')), actor (String), kind (String), from_status and to_status (String, nullable) and at (DateTime(timezone=True)); init_db() creates the comments and ticket_events tables along with tickets, and the Ticket model is unchanged

# TO-3a
