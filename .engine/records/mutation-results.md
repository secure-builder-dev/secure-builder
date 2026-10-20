# Mutation results

© 2026 Casey Houle. All rights reserved.

Developer security testing evidence: every declared control broken on purpose,
one row per control and branch, with whether the project's suite failed. A row whose
result is not suite-failed is a control whose tests do not depend on it.

Schema: mutation-results/1.

| date | control | branch | mutation | baseline | result | side |
|---|---|---|---|---|---|---|
| 2026-10-20T15:58:49+00:00 | CTRL-AUTHN-BEARER | - | other: injected `return None` as the first statement of get_caller | green | suite-failed | local |
| 2026-10-20T15:58:49+00:00 | CTRL-AUTHZ-TICKET-PARTY | - | other: injected `return None` as the first statement of change_status | green | suite-failed | local |
| 2026-10-20T16:41:19+00:00 | CTRL-AUTHN-BEARER | - | other: injected `return None` as the first statement of get_caller | green | suite-failed | local |
| 2026-10-20T16:41:19+00:00 | CTRL-AUTHZ-TICKET-PARTY | - | other: injected `return None` as the first statement of change_status | green | suite-failed | local |
