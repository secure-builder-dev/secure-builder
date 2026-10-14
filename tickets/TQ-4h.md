id: TQ-4h
unit: TQ-4
state: claimed
depends_on: TQ-4d, TQ-4g
done_when: the Household board holds the FilterBar, and Apply fetches /api/board again with the filter, which is kept for every later board fetch until the page reloads; App fetches /api/summary on Load and after every successful status move or new ticket, and shows the SummaryBadge in the top bar after the whoami, while a failed or malformed answer shows no badge and leaves the page working

# TQ-4h
