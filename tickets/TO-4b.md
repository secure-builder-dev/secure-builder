id: TO-4b
unit: TO-4
state: in review
depends_on: -
done_when: household.household_board(session, today, q=None, priority=None, assigned_to=None) gives the same board as before, holding only the tickets that match every filter given: q (ignoring case) appears in the title or the details, priority equals, assigned_to equals — None or an empty string is no filter on that field; household.summary(session, user, today) returns {'overdue': n, 'due_today': n, 'open': n} over the tickets assigned to user whose status is not done or closed: open counts them all, overdue those due before today, due_today those due today

# TO-4b
