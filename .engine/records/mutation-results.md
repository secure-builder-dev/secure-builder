# Mutation results

© 2026 Casey Houle. All rights reserved.

Developer security testing evidence: every declared control broken on purpose,
one row per control and branch, with whether the project's suite failed. A row whose
result is not suite-failed is a control whose tests do not depend on it.

Schema: mutation-results/1.

| date | control | branch | mutation | baseline | result | side |
|---|---|---|---|---|---|---|
| 2026-10-14T07:22:37+00:00 | CTRL-AUTHN-BEARER | - | other: injected `return None` as the first statement of get_caller | green | suite-failed | local |
| 2026-10-14T07:22:37+00:00 | CTRL-AUTHZ-TICKET-PARTY | - | other: injected `return None` as the first statement of change_status | green | suite-failed | local |
| 2026-10-14T07:31:31+00:00 | CTRL-AUTHN-BEARER | - | other: injected `return None` as the first statement of get_caller | green | suite-failed | local |
| 2026-10-14T07:31:31+00:00 | CTRL-AUTHZ-TICKET-PARTY | - | other: injected `return None` as the first statement of change_status | green | suite-failed | local |
| 2026-10-14T10:52:24+00:00 | CTRL-AUTHN-BEARER | - | other: injected `return None` as the first statement of get_caller | green | suite-failed | local |
| 2026-10-14T10:52:24+00:00 | CTRL-AUTHZ-TICKET-PARTY | - | other: injected `return None` as the first statement of change_status | green | suite-failed | local |
| 2026-10-14T17:16:23+00:00 | CTRL-AUTHN-BEARER | - | other: injected `return None` as the first statement of get_caller | green | suite-failed | local |
| 2026-10-14T17:16:23+00:00 | CTRL-AUTHZ-TICKET-PARTY | - | other: injected `return None` as the first statement of change_status | green | suite-failed | local |
