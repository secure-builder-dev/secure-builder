# Mutation results

© 2026 Casey Houle. All rights reserved.

Developer security testing evidence: every declared control broken on purpose,
one row per control and branch, with whether the project's suite failed. A row whose
result is not suite-failed is a control whose tests do not depend on it.

Schema: mutation-results/1.

| date | control | branch | mutation | baseline | result | side |
|---|---|---|---|---|---|---|
| 2026-10-18T07:49:14+00:00 | CTRL-AUTHN-BEARER | - | other: injected `return None` as the first statement of get_caller | green | suite-failed | local |
| 2026-10-18T07:49:14+00:00 | CTRL-AUTHZ-TICKET-PARTY | - | other: injected `return None` as the first statement of change_status | green | suite-failed | local |
| 2026-10-19T03:21:52+00:00 | CTRL-AUTHN-BEARER | - | other: injected `return None` as the first statement of get_caller | green | suite-failed | local |
| 2026-10-19T03:21:52+00:00 | CTRL-AUTHZ-TICKET-PARTY | - | other: injected `return None` as the first statement of change_status | green | suite-failed | local |
| 2026-10-19T09:12:57+00:00 | CTRL-AUTHN-BEARER | - | other: injected `return None` as the first statement of get_caller | green | suite-failed | local |
| 2026-10-19T09:12:57+00:00 | CTRL-AUTHZ-TICKET-PARTY | - | other: injected `return None` as the first statement of change_status | green | suite-failed | local |
