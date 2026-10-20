id: XO-4a
unit: XO-4
state: open
depends_on: -
done_when: rules.edit_ticket(session, ticket_id, user, data) raises, in this order, LookupError when the ticket does not exist or user is not a party, ValueError when data is not a dict, is empty, holds a key other than title, details, priority and due, or holds a value create_ticket would refuse, PermissionError when user is not the filer, and rules.NotEditable when the status is not open or acknowledged; rules.NotEditable is a subclass of Exception and of neither ValueError nor PermissionError; a successful edit changes only the given fields (title stored stripped), sets updated_at, records an event of kind 'edited' with actor the user and no statuses, commits, and returns ticket_to_dict of the ticket; a failed edit changes nothing and records nothing

# XO-4a
