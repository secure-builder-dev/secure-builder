id: GQ-2f
unit: GQ-2
state: in review
depends_on: GQ-2e
done_when: Load and every reload in frontend/src/App.tsx also call fetchBoard and show the HouseholdBoard component with the answer as the last element of main, after Tickets I filed; when /api/board fails, or answers something that is not an object with the arrays todo, in_progress and completed, no Household board is shown, no error message is shown for it, and the rest of the page works as before

# GQ-2f
