id: QW-2h
unit: QW-2
state: open
depends_on: QW-2d, QW-2f, QW-2g
done_when: when Load is pressed frontend/src/App.tsx also calls fetchBoard from frontend/src/api.ts and shows the HouseholdBoard component with the answer, so both users see every ticket of the household; a failed or malformed /api/board answer leaves the household board empty and the rest of the page as it was, with no error message for it; every test in frontend/tests/App.test.tsx still passes; every clause has a Vitest test in frontend/tests/AppBoard.test.tsx that imports '@testing-library/jest-dom/vitest' and calls afterEach(cleanup), and finds elements by label, role or text, and that replaces globalThis.fetch with a vi.fn() answering by URL (/api/dashboard, /api/filed, /api/board and /api/me) with Response objects

# QW-2h
