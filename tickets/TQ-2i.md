id: TQ-2i
unit: TQ-2
state: claimed
depends_on: TQ-2g, TQ-2h
done_when: Load and every reload in frontend/src/App.tsx also call fetchBoard and show the HouseholdBoard component with the answer as the last element of main, after Tickets I filed; when /api/board fails, or answers something that is not an object with the arrays todo, in_progress and completed, no Household board is shown, no error message is shown for it, and the rest of the page works as before

# TQ-2i
