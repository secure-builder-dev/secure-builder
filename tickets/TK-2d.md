id: TK-2d
unit: TK-2
state: claimed
depends_on: TK-2b, TK-2c
done_when: each ticket title on the board in frontend/src/App.tsx (To Do, In Progress and Completed) is wrapped in the HoverCard component from frontend/src/HoverCard.tsx with that ticket, so that hovering the title shows the ticket's details in a tooltip; the other parts of the page are unchanged, and every test in frontend/tests/App.test.tsx still passes; every clause has a Vitest test in frontend/tests/AppHover.test.tsx that imports '@testing-library/jest-dom/vitest' and calls afterEach(cleanup), and finds elements by label, role or text, and that replaces globalThis.fetch with a vi.fn() answering by URL (/api/dashboard, /api/filed, /api/board and /api/me) with Response objects

# TK-2d
