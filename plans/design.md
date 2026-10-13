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

# Epics 3 and 4 (added to the same plan)

E1 (tickets API) and E2 (web board) are everything above. E3 adds comments and a history to every ticket; E4 adds
editing, a filter on the household board and a summary in the top bar. Nothing above changes, except where this
section says so. The earlier tests keep passing.

## Tests in this project

Each bead names its acceptance tests (given, read-only) and, for most beads, a unit test file that the coder writes
for its own code, before the code. The gate measures coverage and mutation on the whole suite: the unit tests are what
cover the rules and components below the level the acceptance tests check.

How a unit test is written here (the acceptance tests are examples of every point):

- Backend: pytest test functions (`def test_...(db):`), run from `backend/` with `pythonpath = .`. Application code
  is imported as `app.<module>`: `from app.rules import create_ticket`, `from app.models import Ticket`, never
  `backend.app...`. The database is the PostgreSQL test database that `TICKETER_DATABASE_URL` already names; never
  SQLite, never a URL of your own. Use the fixtures of `backend/tests/conftest.py`: `db` (a session on fresh tables),
  `client` (a TestClient with both tokens set), the headers `HER`, `HIM`, `BAD`, and the helpers `at(day)` and
  `set_times(...)` (`from tests.conftest import HER, at, set_times`). A test of what happens when the variable is
  unset uses pytest's `monkeypatch` and `importlib.reload`, and reloads the module with the variable restored at the end.
- Frontend: Vitest with Testing Library, files `frontend/tests/<Name>.unit.test.ts(x)`. Start with
  `import "@testing-library/jest-dom/vitest";`, import components from `../src/<Name>`, and the shared helpers from
  `./helpers` (`ticket()`, `board()`, `comment()`, `event()`, `mockApi()`, `settle()`, `region()`, `card()`). JSX only in
  `.tsx` files. Call `cleanup()` after each test.
- A unit test checks the bead's clauses through the module's own functions or props, and fails only because the
  behaviour is missing, never because of its own imports or setup.

## E3 files

| Part | Files |
| --- | --- |
| Models | `backend/app/models.py` adds `Comment` and `TicketEvent` |
| Rules | `backend/app/activity.py` (new); `backend/app/rules.py` records events |
| API | `backend/app/main.py` |
| Frontend | `api.ts`, `TicketCard.tsx`, `HouseholdBoard.tsx`, `CommentThread.tsx`, `HistoryList.tsx`, `TicketDetail.tsx`, `App.tsx` |

## Comment and TicketEvent

`Comment`, table `comments`: `id` (integer primary key), `ticket_id` (integer, foreign key `tickets.id`), `author`
(String), `body` (String(500)), `created_at` (DateTime(timezone=True)).

`TicketEvent`, table `ticket_events`: `id` (integer primary key), `ticket_id` (integer, foreign key `tickets.id`),
`actor` (String), `kind` (String: `filed` | `status` | `edited`), `from_status` and `to_status` (String, nullable),
`at` (DateTime(timezone=True)).

As dicts or JSON (`activity.comment_to_dict`, `activity.event_to_dict`): every column, with `created_at` / `at` as
ISO-8601 strings.

## Activity rules (`backend/app/activity.py`)

- `record_event(session, ticket, actor, kind, from_status=None, to_status=None)` adds a `TicketEvent` for that ticket
  with `at` = now (timezone-aware UTC). It does not commit: the caller's commit stores it with the change it records.
- `rules.create_ticket` records `filed` (actor = the filer, from None, to `open`) in the same commit as the ticket.
  `rules.change_status` records `status` (actor = the caller, from = the old status, to = the new one) for every
  successful move, in the same commit. A failed create or move records nothing.
- `add_comment(session, ticket_id, user, body)`: `LookupError` when the ticket does not exist or `user` is not its
  filer or assignee; `ValueError` when `body` is not a str, or is empty or over 500 characters after stripping. Stores
  the stripped body with `created_at` = now, commits, and returns `comment_to_dict`. A comment does not change the
  ticket (not even `updated_at`).
- `list_comments(session, ticket_id, user)` and `ticket_history(session, ticket_id, user)`: `LookupError` as above;
  the ticket's comments (or events) oldest first, by `created_at` (or `at`) then `id`, as dicts.

## E3 API

| Route | Answer |
| --- | --- |
| `GET /api/tickets/{id}` | 200 the ticket (`ticket_to_dict`); 404 `not found` |
| `GET /api/tickets/{id}/comments` | 200 `{"comments": [...]}`; 404 `not found` |
| `POST /api/tickets/{id}/comments` body `{"body": s}` | 201 the comment; 400 `invalid request` (as for tickets: malformed JSON, not an object, other keys, an invalid body); 404 `not found` |
| `GET /api/tickets/{id}/history` | 200 `{"events": [...]}`; 404 `not found` |

All of them need the bearer token (401 as above) and follow the error, header and body-limit rules above. A
non-integer id is 400 `invalid request`.

## E3 frontend

`api.ts` adds `fetchTicket`, `fetchComments`, `addComment(token, id, body)` and `fetchHistory`, the same way as the
others (`Comments`, `CommentOut`, `History`, `TicketEvent` in `types.ts`).

`TicketCard` gains an optional prop `onOpen(ticket)`. With it, the card has the class `openable`, and a click on the
title (`h3.card-title`) or Enter while the title's `span.hover-target` has focus calls `onOpen(ticket)`. Without it
nothing changes. The card gets no new button.

`HouseholdBoard` gains optional props `onOpen` (passed to every card) and `children` (rendered between its `h2` and
the board; E4 puts the filter bar there).

`CommentThread` (props `comments`, `onAdd(body)`):
```
<div className="comment-thread">
  <ol className="comments" aria-label="Comments">
    <li className="comment"><span className="comment-author">her</span> <p className="comment-body">text</p></li>
  </ol>                                            (or <p className="empty">No comments yet</p> when there are none)
  <form className="comment-form"> <label>Comment <textarea/></label> <button type="submit">Add comment</button> </form>
</div>
```
Submitting calls `onAdd` with the stripped text and empties the field; blank text calls nothing.

`HistoryList` (prop `events`): `<ol className="history" aria-label="History">`, one `<li>` per event, oldest first:
`her filed it`, `him moved it from open to acknowledged` (statuses with `_` as a space: `in progress`),
`her edited it`. No events: `<p className="empty">No history</p>`.

`TicketDetail` (props `token`, `ticket`, `me` (the signed-in user or null), `onClose`, and from E4 `onSaved(ticket)`):
```
<section className="panel ticket-detail" aria-label="Ticket details">
  <h2>{title}</h2>
  <p className="detail-text">{details}</p>          (only when details is not empty)
  <div className="card-meta"> the same badge, due, pill and who spans as TicketCard </div>
  <h3>Comments</h3> <CommentThread/>
  <h3>History</h3>  <HistoryList/>
  <button className="close-detail">Close details</button>
</section>
```
It fetches the comments and the history when it opens and whenever `ticket.id` changes. Adding a comment POSTs it and
then shows the comment from the answer at the end of the list; a failed comment shows `<p role="alert"
className="error">Could not add the comment</p>` inside the panel and adds nothing to the list. A failed or malformed
comments or history answer leaves that list empty; the rest of the panel works.

`App`: every TicketCard on the page (My board, Tickets I filed, Household board) opens its ticket in the
`TicketDetail` panel, shown in `main` after the error message and the directions and before New ticket. Opening
another ticket replaces it; Close details hides it; pressing Load again closes it. A status move made from a card
re-fetches the open panel's history.

## E4 files

| Part | Files |
| --- | --- |
| Rules | `backend/app/rules.py` (`edit_ticket`), `backend/app/household.py` (filter, `summary`) |
| API | `backend/app/main.py` |
| Frontend | `api.ts`, `EditTicketForm.tsx`, `FilterBar.tsx`, `SummaryBadge.tsx`, `TicketDetail.tsx`, `App.tsx` |

## E4 rules

`rules.edit_ticket(session, ticket_id, user, data)`, checked in this order: `LookupError` when the ticket does not
exist or `user` is not a party; `ValueError` when `data` is not a dict, is empty, holds a key other than `title`,
`details`, `priority`, `due`, or a value create_ticket would refuse; `PermissionError` when `user` is not the filer;
`rules.NotEditable` (a subclass of `Exception`, not of `ValueError` or `PermissionError`) when the status is not
`open` or `acknowledged`. Otherwise it changes only the given fields (title stored stripped), sets `updated_at`,
records an `edited` event (actor = the user, no statuses), commits, and returns `ticket_to_dict`. A failed edit changes
nothing and records nothing.

`household.household_board(session, today, q=None, priority=None, assigned_to=None)`: the same board, holding only
tickets that match every filter given: `q` (case-insensitive) is in the title or the details; `priority` equals;
`assigned_to` equals. None or an empty string means no filter on that field.

`household.summary(session, user, today)`: `{"overdue": n, "due_today": n, "open": n}` over the tickets assigned to
`user` whose status is not `done` or `closed`: `open` counts them all, `overdue` those due before today, `due_today`
those due today.

## E4 API

| Route | Answer |
| --- | --- |
| `PATCH /api/tickets/{id}` body: any of `title`, `details`, `priority`, `due` | 200 the ticket; 404 `not found`; 400 `invalid request`; 403 `forbidden`; 409 `not editable` |
| `GET /api/board?q=&priority=&assigned_to=` | the filtered household board; `q` over 120 characters, a `priority` not in the three, or an `assigned_to` not `her` / `him` -> 400 `invalid request`; other query parameters are ignored |
| `GET /api/summary` | 200 the caller's summary (today = current UTC date) |

Same token, error, header and body-limit rules.

## E4 frontend

`api.ts` adds `editTicket(token, id, changes)` (PATCH), `fetchSummary(token)`, and an optional filter argument to
`fetchBoard(token, filter?)` that sends only the non-empty fields as query parameters (`BoardFilter`, `TicketEdit`,
`Summary` in `types.ts`).

`EditTicketForm` (props `ticket`, `onSave(changes)`, `onCancel`, optional `error`):
`<form className="edit-ticket" aria-label="Edit ticket">` with the labelled fields Title, Details, Priority (select) and
Due (date), filled from the ticket, and the buttons Save (submit) and Cancel. Save calls `onSave` with all four fields
(`due` null when empty). With `error`, the form shows `<p role="alert" className="error">{error}</p>`.

`TicketDetail` shows an Edit button (after the card-meta) only when `me` is the ticket's filer and its status is
`open` or `acknowledged`. Edit shows the `EditTicketForm` in the panel. Save PATCHes the four fields; on success the
form closes, the panel shows the answered ticket, its history is fetched again, and `onSaved(ticket)` is called (App
then re-fetches the boards and the summary); on failure the form stays open with the error `Could not save`.

`FilterBar` (prop `onApply(filter)`): `<form className="filter-bar" role="search" aria-label="Filter household board">`
with the labelled fields Search (text), Priority (select: `Any`, `low`, `normal`, `urgent`; `Any` is the empty value)
and Assigned to (select: `Anyone`, `her`, `him`), and an Apply submit button. Apply calls `onApply` with
`{ q, priority, assigned_to }` (q stripped; empty strings for no filter).

App puts the FilterBar inside the Household board (as its children). Apply re-fetches `/api/board` with the filter;
the filter is kept for every later board fetch until the page reloads.

`SummaryBadge` (prop `summary`): `<span className="summary" aria-label="Summary">2 overdue · 1 due today · 5 open</span>`
plus the class `alert` when `overdue` is more than 0. App fetches `/api/summary` on Load and after every successful
status move, new ticket or edit, and shows the badge in the top bar after the whoami; a failed or malformed answer
shows no badge.
