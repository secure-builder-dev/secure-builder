id: FQ-2g
unit: FQ-2
state: open
depends_on: -
done_when: frontend/src/api.ts exports fetchBoard(token) which sends GET /api/board with Authorization: Bearer <token> and returns the parsed JSON, throwing an Error whose message is the status code when the answer is not ok; frontend/src/HouseholdBoard.tsx default-exports a React component HouseholdBoard written in TypeScript that takes a board ({todo, in_progress, completed}) and renders a section headed Household board with three columns headed To Do, In Progress and Completed; each ticket in those columns shows its title and the text for her or for him according to its assigned_to, as React text; every clause has a Vitest test in frontend/tests/HouseholdBoard.test.tsx that imports '@testing-library/jest-dom/vitest' and calls afterEach(cleanup), and finds elements by label, role or text

# FQ-2g
