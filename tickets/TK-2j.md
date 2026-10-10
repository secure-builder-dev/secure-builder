id: TK-2j
unit: TK-2
state: open
depends_on: TK-2h, TK-2i
done_when: frontend/src/api.ts exports fetchMe(token) which sends GET /api/me with Authorization: Bearer <token> and returns the parsed JSON; after Load, frontend/src/App.tsx shows the text Signed in as her or Signed in as him from /api/me, and the new-ticket form's heading reads New ticket for him when the caller is her and New ticket for her when the caller is him (New ticket before /api/me has answered); a failed /api/me answer shows no Signed in text and leaves the rest of the page working

# TK-2j
