# Honey-Do Tickets — design plan

A two-person ticket desk. One partner files a ticket for the other; the other works it on a three-column board.
Two fixed users: `her` and `him`. A ticket is always assigned to the user who did not file it.

## Stack and files

| Part | Technology | Files |
| --- | --- | --- |
| Database | PostgreSQL 17 through SQLAlchemy 2 (psycopg 3 driver) | `backend/app/db.py`, `backend/app/models.py` |
| Rules | Plain Python, no HTTP | `backend/app/rules.py` |
| API | FastAPI | `backend/app/main.py` |
| Frontend | React 19 + TypeScript, built with Vite | `frontend/src/App.tsx`, `frontend/src/api.ts`, `frontend/src/types.ts` (more components allowed under `frontend/src/`) |
| Backend tests | pytest | `backend/tests/test_rules.py`, `backend/tests/test_api.py` |
| Frontend tests | Vitest + Testing Library (jsdom) | `frontend/tests/App.test.tsx` |

`frontend/src/main.tsx` mounts `<App />` (default export of `App.tsx`) and is not to be changed. The test command is
`scripts/test_all.py`: pytest runs in `backend/` (imports are `from app.rules import ...`), then Vitest in `frontend/`.
The tests use the database in `TICKETER_DATABASE_URL`, which the test command sets to a dedicated test database.
Only the pinned dependencies in `backend/requirements*.txt` and `frontend/package.json` may be used.

## Ticket

`id` (integer primary key), `title` (1-120 chars), `details` (0-1000 chars, default ""), `priority`
(`low` | `normal` | `urgent`, default `normal`), `due` (date or null), `status`, `filed_by`, `assigned_to`,
`created_at`, `updated_at` (timezone-aware UTC datetimes). As a dict or JSON: `due` is `YYYY-MM-DD` or null,
timestamps are ISO-8601 strings.

## Status moves (nothing else is allowed)

| From | To | Who |
| --- | --- | --- |
| open | acknowledged | assignee |
| acknowledged | in_progress | assignee |
| in_progress | done | assignee |
| done | closed | filer |
| done | open | filer (reopen) |
| closed | open | filer (reopen) |

Errors, checked in this order: ticket missing or caller not a party -> `LookupError`; unknown status or a move not in the
table -> `ValueError`; a move in the table made by the wrong party -> `PermissionError`. A failed move changes nothing.
Every successful move sets `updated_at`.

## Board (for one user, on a given day)

| Column | Key | Tickets assigned to the user with status |
| --- | --- | --- |
| To Do | `todo` | open, acknowledged |
| In Progress | `in_progress` | in_progress |
| Completed | `completed` | done, closed — only those whose `updated_at` date is within the 7 days ending today |

`todo` and `in_progress` are each ordered by group (0 = urgent or overdue, i.e. due before today; 1 = due today or within
the next 3 days; 2 = the rest), then due date (no due date last), then `created_at` oldest first; each ticket in them
carries `group`. `completed` is newest `updated_at` first.

## API (FastAPI)

The bearer token names the caller: `TOKEN_HER` -> `her`, `TOKEN_HIM` -> `him` (hmac.compare_digest; an unset or empty
variable never matches). One database session per request. Errors are JSON `{"error": "<fixed text>"}` and never echo
input or a stack trace (FastAPI's default 422 echoes the input: replace it). Body limit 64 KiB. Security headers on every
response.

## Frontend

The user pastes their token into a field (kept in React state only, never in localStorage). The page shows the
new-ticket form, the board as three columns (To Do, In Progress, Completed), and "Tickets I filed" with Close and Reopen
on done tickets. Text from the API is rendered as React text, never as HTML.

## FD-2 additions (unit FD-2: sleek coder styling, hover cards, household board, signed-in user, menu with directions)

Built in small beads; each bead names the only files it may change. New code goes in new files where it can.

| Part | Files |
| --- | --- |
| Styles | `frontend/src/styles.css`, imported once by `App.tsx` (`import './styles.css';`) |
| Hover card | `frontend/src/HoverCard.tsx` (default export `HoverCard`) |
| Household board | `backend/app/household.py` (`household_board(session, today)`), `GET /api/board` in `main.py`, `frontend/src/HouseholdBoard.tsx` |
| Signed-in user | `GET /api/me` in `main.py`, shown by `App.tsx` |
| Menu and directions | `frontend/src/Menu.tsx`, `frontend/src/Directions.tsx` |

Sleek coder look: a dark, terminal-flavoured theme. `:root` holds the palette as custom properties (`--bg: #0d1117`,
`--panel: #161b22`, `--border: #30363d`, `--fg: #e6edf3`, `--accent: #3fb950`, `--danger: #f85149`); the page uses a
monospace stack (`"JetBrains Mono", "Fira Code", ui-monospace, Consolas, monospace`). The top bar (`topbar`) carries a
green `brand` heading reading `~/honey-do`; tickets are dark `card`s whose border lights up in the accent on hover, and an
urgent ticket has a red left border.

Household board: every ticket of both users, in the same three columns as the personal board (To Do = open or
acknowledged, In Progress = in_progress, Completed = done or closed with `updated_at` within the 7 days ending today).
To Do and In Progress are oldest `created_at` first; Completed is newest `updated_at` first. Each ticket dict is the
usual one (it carries `filed_by` and `assigned_to`). Both users see the same board.

`GET /api/board` and `GET /api/me` need the bearer token like every other `/api` route (401 `{"error": "unauthorized"}`
without it). `/api/me` answers `{"user": "her"}` or `{"user": "him"}`.

Frontend tests: every test file imports `'@testing-library/jest-dom/vitest'` and calls `afterEach(cleanup)` (nothing
else sets them up), and a test that renders `App` replaces `globalThis.fetch` with a `vi.fn()` that answers by URL
(`/api/dashboard`, `/api/filed`, `/api/board`, `/api/me`), so that adding a request never breaks an older test. `App`
treats a failed or malformed answer from `/api/board` or `/api/me` as empty and still shows the rest of the page.
