id: GQ-1c
unit: GQ-1
state: in review
depends_on: GQ-1b
done_when: rules.change_status(session, ticket_id, user, new_status) applies exactly the moves of the design's status table: open to acknowledged, acknowledged to in_progress and in_progress to done by the assignee — done to closed, done to open and closed to open by the filer; it raises LookupError when the ticket does not exist or user is neither its filer nor its assignee, checked first; then it raises ValueError when new_status is not one of open, acknowledged, in_progress, done and closed, or the move from the current status is not in the table (a move to the same status included); then it raises PermissionError when the move is in the table but user is not the party the table names; a successful move sets status and updated_at (the current UTC time), commits, and returns ticket_to_dict of the ticket — a raising call changes nothing

# GQ-1c
