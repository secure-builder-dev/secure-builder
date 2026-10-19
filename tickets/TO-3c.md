id: TO-3c
unit: TO-3
state: open
depends_on: TO-3b
done_when: rules.create_ticket records one event of kind 'filed' with actor the filer, from_status None and to_status 'open', stored in the same commit as the ticket; rules.change_status records one event of kind 'status' with actor the caller, from_status the old status and to_status the new one for every successful move, in the same commit as the move; a create_ticket or change_status call that raises records no event, and every earlier behaviour of create_ticket and change_status is unchanged

# TO-3c
