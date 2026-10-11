id: QW-2a
unit: QW-2
state: in review
depends_on: -
done_when: frontend/src/styles.css defines on :root the custom properties --bg: #0d1117, --panel: #161b22, --border: #30363d, --fg: #e6edf3, --accent: #3fb950 and --danger: #f85149, and its body rule sets background: var(--bg), color: var(--fg) and a font-family whose stack starts with "JetBrains Mono" and ends with monospace; it holds a .board rule with display: grid and grid-template-columns: repeat(3, 1fr) and a gap; it holds a .card rule with background: var(--panel), a border using var(--border), a border-radius and a padding, and a .card:hover rule that sets border-color: var(--accent) and a box-shadow; it holds a .urgent rule whose border-left uses var(--danger), a .topbar rule with display: flex and a border-bottom using var(--border), and a .brand rule with color: var(--accent); every clause has a Vitest test in frontend/tests/styles.test.ts that imports '@testing-library/jest-dom/vitest' and calls afterEach(cleanup), and finds elements by label, role or text (it reads src/styles.css as text with node:fs)

# QW-2a
