id: GV-2c
unit: GV-2
state: in review
depends_on: -
done_when: backend/app/household.py defines household_board(session, today), which takes a datetime.date and returns {'todo': [...], 'in_progress': [...], 'completed': [...]} built from every ticket of both users, each as rules.ticket_to_dict returns it (no group key); todo holds the tickets with status open or acknowledged and in_progress those with status in_progress, each ordered oldest created_at first; completed holds the tickets with status done or closed whose updated_at date (UTC) is today or one of the 6 days before today, newest updated_at first

# GV-2c
