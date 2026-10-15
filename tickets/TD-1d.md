id: TD-1d
unit: TD-1
state: open
depends_on: TD-1c
done_when: rules.dashboard(session, user, today) takes a datetime.date and returns {'todo': [...], 'in_progress': [...], 'completed': [...]} of ticket_to_dict dicts built only from the tickets assigned to user; todo holds the tickets with status open or acknowledged and in_progress those with status in_progress — each of their dicts gets the extra key group: 0 when priority is 'urgent' or due is before today, 1 when due is today or within the 3 days after today, 2 otherwise; todo and in_progress are each ordered by group, then by due date (tickets without a due date last), then by created_at oldest first; completed holds the tickets with status done or closed whose updated_at date (UTC) is today or one of the 6 days before today, newest updated_at first, without a group key; rules.filed(session, user) returns ticket_to_dict of every ticket user filed, whatever its status, newest created_at first

# TD-1d
