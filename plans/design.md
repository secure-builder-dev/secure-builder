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
