# Honey-Do Tickets — design plan

A two-person ticket desk. One partner files a ticket for the other; the other works it on a three-column board.
Two fixed users: `her` and `him`. A ticket is always assigned to the user who did not file it.

End state: one page with a top bar (brand, menu, token field, who is signed in), a New ticket form, the caller's own
board (To Do / In Progress / Completed), the tickets the caller filed, and a Household board with every ticket of both
users. Every ticket anywhere on the page is one `TicketCard`; hovering or focusing its title shows a hover card.

## Stack and files

| Part | Files |
| --- | --- |
| Database (PostgreSQL 17, SQLAlchemy 2, psycopg 3) | `backend/app/db.py` (`engine`, `Base`, `SessionLocal`, `init_db()`), `backend/app/models.py` (`Ticket`) |
| Rules (plain Python, no HTTP) | `backend/app/rules.py`, `backend/app/household.py` |
| API (FastAPI) | `backend/app/main.py` |
| Frontend (React 19 + TypeScript, Vite) | `frontend/src/types.ts` (given; do not change), `api.ts`, `App.tsx`, `TicketCard.tsx`, `HoverCard.tsx`, `HouseholdBoard.tsx`, `Menu.tsx`, `Directions.tsx` |
| Styles | `frontend/src/styles.css` (given; do not change). Components only set the class names listed below. |
| Tests | `backend/tests/` (pytest; shared fixtures in `conftest.py`), `frontend/tests/` (Vitest + Testing Library; shared helpers in `helpers.tsx`) |

`frontend/src/main.tsx` mounts `<App />` and is not to be changed. Only the pinned dependencies in
`backend/requirements*.txt` and `frontend/package.json` may be used. Tests are the specification and are read-only.

## Ticket

`id` (integer primary key), `title` (1-120 chars after stripping), `details` (0-1000 chars, default ""), `priority`
(`low` | `normal` | `urgent`, default `normal`), `due` (date or null), `status`, `filed_by`, `assigned_to`,
`created_at`, `updated_at` (timezone-aware UTC). As a dict or JSON (`rules.ticket_to_dict`): `due` is `YYYY-MM-DD` or
null, timestamps are ISO-8601 strings.

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

## Boards

Personal board (`rules.dashboard(session, user, today)`): only tickets assigned to the user. `todo` = open or
acknowledged, `in_progress` = in_progress, `completed` = done or closed with `updated_at` date within the 7 days ending
today (today and the 6 days before). `todo` and `in_progress` are ordered by group (0 = urgent or due before today;
1 = due today or within the next 3 days; 2 = the rest), then due date (none last), then `created_at` oldest first; each
of their tickets carries `group`. `completed` is newest `updated_at` first.

Household board (`household.household_board(session, today)`): every ticket of both users, same three columns and
Completed window; `todo` and `in_progress` oldest `created_at` first (no `group` key), `completed` newest `updated_at` first.

## API

Bearer token names the caller (`get_caller`): `TOKEN_HER` -> `her`, `TOKEN_HIM` -> `him`, compared with
`hmac.compare_digest`; an unset or empty variable never matches. Every `/api` route needs it (401
`{"error": "unauthorized"}`); `GET /health` is public. One database session per request. Errors are JSON
`{"error": "<fixed text>"}` and never echo input or a stack trace.

| Route | Answer |
| --- | --- |
| `GET /health` | 200 `{"status": "ok"}` |
| `POST /api/tickets` | 201 the new ticket (filed by the caller) |
| `POST /api/tickets/{id}/status` body `{"status": s}` | 200 the ticket; 404 `not found`, 403 `forbidden`, 409 `invalid transition` |
| `GET /api/dashboard` | 200 the caller's personal board (today = current UTC date) |
| `GET /api/filed` | 200 `{"tickets": [...]}` the caller's filed tickets, newest `created_at` first |
| `GET /api/board` | 200 the household board |
| `GET /api/me` | 200 `{"user": "her"}` or `{"user": "him"}` |

Malformed JSON, a body that is not an object, invalid fields or a non-integer id -> 400 `invalid request` (replaces
FastAPI's 422). Body over 65536 bytes -> 413 `too large`. Unknown path -> 404 `not found`; wrong method -> 405
`method not allowed`. Every response: `X-Content-Type-Options: nosniff`, `Content-Security-Policy: default-src 'none'`,
`Cache-Control: no-store`, `Referrer-Policy: no-referrer`.

## Frontend

Types are in `types.ts`. `api.ts` holds every fetch call; each sends `Authorization: Bearer <token>`, returns the
parsed JSON, and on a non-ok answer throws `new Error(String(status))` (so a 401 throws `Error("401")`). The token lives
in React state only (never localStorage/sessionStorage). Text from the API is React text only (never
`dangerouslySetInnerHTML`, `innerHTML` or `eval`). A failed or malformed `/api/board` or `/api/me` answer leaves that
part empty and the rest of the page working.

Page structure and class names (the CSS styles exactly these):

```
<div className="app">
  <header className="topbar">
    <h1 className="brand">~/honey-do</h1>
    <Menu />                                    (button "Menu", class menu-button; nav "Main menu", class menu)
    <div className="token-form"> Token input + Load button </div>
    <span className="whoami">Signed in as her</span>     (only once /api/me has answered)
  </header>
  <main className="content">
    <p role="alert" className="error">Wrong token</p>   (only on an error)
    <Directions />                              (section.panel.directions, only when chosen)
    <section className="panel new-ticket" aria-label="New ticket"> <h2>New ticket for him</h2> form </section>
    <section className="panel" aria-label="My board"> <h2>My board</h2>
      <div className="board"> three <section className="column" aria-label="To Do|In Progress|Completed">
        <h3 className="column-title">To Do <span className="count">2</span></h3>
        TicketCards, or <p className="empty">Nothing here</p> </section> </div> </section>
    <section className="panel" aria-label="Tickets I filed"> <h2>Tickets I filed</h2>
      <div className="card-list"> TicketCards (Close / Reopen on done ones) </div> </section>
    <HouseholdBoard />                          (section.panel "Household board", same board/column markup)
  </main>
</div>
```

`TicketCard` (props `ticket`, optional `children` = action buttons) renders
`<article className="card" aria-label={title}>` plus class `urgent` when `ticket.group === 0`, with
`<h3 className="card-title">` (the title), `<div className="card-meta">` holding `<span className="badge priority-<p>">`
(the priority), `<span className="due">due YYYY-MM-DD</span>` (only with a due date), `<span className="pill status-<s>">`
(the status with `_` as a space, e.g. `in progress`) and `<span className="who">for him</span>` (from `assigned_to`), and
`<div className="card-actions">` holding the children (only when there are children). Hover card: `HoverCard` wraps the
title; `span.hover-target` and, while shown, `div.hover-card[role=tooltip]`.
