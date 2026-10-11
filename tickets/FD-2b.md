id: FD-2b
unit: FD-2
state: in review
depends_on: FD-2a
done_when: frontend/src/App.tsx imports './styles.css' and wraps the token field and Load button in an element with the class topbar, which also holds a heading with the class brand reading ~/honey-do; the three board columns sit inside one element with the class board and each column has the class column; every ticket on the board has the class card, and a ticket whose group is 0 has the classes card and urgent; every clause has a Vitest test in frontend/tests/Layout.test.tsx that imports '@testing-library/jest-dom/vitest' and calls afterEach(cleanup), and finds elements by label, role or text, and that replaces globalThis.fetch with a vi.fn() answering by URL (/api/dashboard, /api/filed, /api/board and /api/me) with Response objects

# FD-2b
