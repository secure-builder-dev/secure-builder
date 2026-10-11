id: FD-2k
unit: FD-2
state: claimed
depends_on: -
done_when: frontend/src/Menu.tsx default-exports a React component Menu written in TypeScript that takes onDirections and renders a button labelled Menu (aria-label Menu, showing the character ☰) whose aria-expanded is false while the menu is closed; clicking the Menu button opens a navigation element labelled Main menu holding a button Directions and sets aria-expanded to true, and clicking Menu again closes it; clicking Directions calls onDirections once and closes the menu; every clause has a Vitest test in frontend/tests/Menu.test.tsx that imports '@testing-library/jest-dom/vitest' and calls afterEach(cleanup), and finds elements by label, role or text

# FD-2k
