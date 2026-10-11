id: QW-2m
unit: QW-2
state: open
depends_on: QW-2j, QW-2k, QW-2l
done_when: frontend/src/App.tsx shows the Menu component from frontend/src/Menu.tsx inside the topbar element, and no Directions section until Directions is chosen; choosing Directions in the menu shows the Directions component from frontend/src/Directions.tsx, and its Close button hides it again; every test in frontend/tests/App.test.tsx still passes; every clause has a Vitest test in frontend/tests/AppMenu.test.tsx that imports '@testing-library/jest-dom/vitest' and calls afterEach(cleanup), and finds elements by label, role or text, and that replaces globalThis.fetch with a vi.fn() answering by URL (/api/dashboard, /api/filed, /api/board and /api/me) with Response objects

# QW-2m
