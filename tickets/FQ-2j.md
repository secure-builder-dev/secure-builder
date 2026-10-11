id: FQ-2j
unit: FQ-2
state: in review
depends_on: FQ-2h, FQ-2i
done_when: frontend/src/api.ts exports fetchMe(token) which sends GET /api/me with Authorization: Bearer <token> and returns the parsed JSON; after Load, frontend/src/App.tsx shows the text Signed in as her or Signed in as him from /api/me, and the new-ticket form's heading reads New ticket for him when the caller is her and New ticket for her when the caller is him (New ticket before /api/me has answered); a failed /api/me answer shows no Signed in text and leaves the rest of the page working, and every test in frontend/tests/App.test.tsx still passes; every clause has a Vitest test in frontend/tests/SignedIn.test.tsx that imports '@testing-library/jest-dom/vitest' and calls afterEach(cleanup), and finds elements by label, role or text, and that replaces globalThis.fetch with a vi.fn() answering by URL (/api/dashboard, /api/filed, /api/board and /api/me) with Response objects

# FQ-2j
