id: TK-2b
unit: TK-2
state: claimed
depends_on: TK-2a
done_when: frontend/src/App.tsx imports './styles.css' and wraps the token field and Load button in an element with the class topbar; the three board columns sit inside one element with the class board and each column has the class column; every ticket on the board has the class card, and a ticket whose group is 0 has the classes card and urgent; every clause has a Vitest test in frontend/tests/Layout.test.tsx that imports '@testing-library/jest-dom/vitest' and calls afterEach(cleanup), and finds elements by label, role or text, and that replaces globalThis.fetch with a vi.fn() answering by URL (/api/dashboard, /api/filed, /api/board and /api/me) with Response objects

# TK-2b
