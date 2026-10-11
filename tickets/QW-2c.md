id: QW-2c
unit: QW-2
state: claimed
depends_on: -
done_when: frontend/src/HoverCard.tsx default-exports a React component HoverCard written in TypeScript that takes a ticket (an object with details, filed_by, assigned_to and created_at) and children and renders the children inside a span with the class hover-target; while the pointer is over that span (mouseenter until mouseleave) or it has keyboard focus (focus until blur), an element with the role tooltip and the class hover-card is shown, and it is absent otherwise; the tooltip shows the ticket's details (or the text No details when details is empty), the text Filed by followed by filed_by, the text Assigned to followed by assigned_to, and the text Created followed by the first 10 characters of created_at, all as React text; every clause has a Vitest test in frontend/tests/HoverCard.test.tsx that imports '@testing-library/jest-dom/vitest' and calls afterEach(cleanup), and finds elements by label, role or text

# QW-2c
