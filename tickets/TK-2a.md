id: TK-2a
unit: TK-2
state: open
depends_on: -
done_when: frontend/src/styles.css holds a .board rule with display: grid and grid-template-columns: repeat(3, 1fr) and a gap; it holds a .card rule with a border-radius, a box-shadow and a padding, and a .card:hover rule that changes the box-shadow; it holds a .urgent rule whose border-left uses the color #c0392b, and a .topbar rule with display: flex; every clause has a Vitest test in frontend/tests/styles.test.ts that imports '@testing-library/jest-dom/vitest' and calls afterEach(cleanup), and finds elements by label, role or text (it reads src/styles.css as text with node:fs)

# TK-2a
