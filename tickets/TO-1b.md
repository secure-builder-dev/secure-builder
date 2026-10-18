id: TO-1b
unit: TO-1
state: claimed
depends_on: TO-1a
done_when: backend/app/rules.py defines USERS = ('her', 'him') and ticket_to_dict(ticket), which returns a Ticket as a plain dict with every column: due as a YYYY-MM-DD string or None, created_at and updated_at as ISO-8601 strings (datetime.isoformat()); create_ticket(session, filed_by, data) takes a dict that may hold only the keys title, details, priority and due, and raises ValueError when filed_by is not in USERS or data holds any other key; title is required and must be a str of 1 to 120 characters after stripping whitespace (it is stored stripped), details is an optional str of at most 1000 characters (default ''), priority is optional, one of 'low', 'normal' or 'urgent' (default 'normal'), and due is optional, None or a str in the form YYYY-MM-DD naming a real date (default None), and any other type or value raises ValueError, and nothing is stored; a created ticket has status 'open', is assigned to the other user of USERS, has created_at and updated_at set to the same current time as a timezone-aware UTC datetime, is committed, and is returned as ticket_to_dict gives it

# TO-1b
