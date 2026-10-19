id: TO-3b
unit: TO-3
state: in review
depends_on: TO-3a
done_when: backend/app/activity.py defines comment_to_dict(comment) and event_to_dict(event), which return every column as a plain dict with created_at (or at) as an ISO-8601 string; record_event(session, ticket, actor, kind, from_status=None, to_status=None) adds a TicketEvent for that ticket with at set to the current timezone-aware UTC time, and does not commit (the event is stored by the caller's next commit and lost on rollback); add_comment(session, ticket_id, user, body) raises LookupError when the ticket does not exist or user is neither its filer nor its assignee, raises ValueError when body is not a str or is empty or over 500 characters after stripping, and otherwise stores the stripped body with author user and created_at now, commits, and returns comment_to_dict of it; a comment leaves the ticket itself unchanged, including its updated_at; list_comments(session, ticket_id, user) and ticket_history(session, ticket_id, user) raise LookupError as add_comment does, and return that ticket's comments (or events) only, oldest first by created_at (or at) and then id, as dicts

# TO-3b
