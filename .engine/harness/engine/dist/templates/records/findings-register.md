# Findings register

© 2026 Casey Houle. All rights reserved.

Rows are added by a human, or by an agent transcribing an identified human
decision, named in `decided_by`. An automated agent never accepts its own finding.

## Table A — Permanent checks

Every P0/P1 finding, from any source, becomes a row here before its fix commits.
The class is written generally enough to catch the next instance. Read at gate
start: a row whose mechanism is missing or broken is a blocking finding.

Schema: findings-register-a/1.

| id | class | mechanism | lives_in | status | decided_by | side |
|---|---|---|---|---|---|---|

## Table B — Accepted risks and compensating controls

A row may be marked accepted only when the proof column is satisfied. Read at
gate start and at every release decision; unsatisfied proof is reported every run.
Ungated inbound code the team knowingly accepts is recorded here too.

Schema: findings-register-b/1.

| id | risk | attack_path | compensating_control | proof | re_review_trigger | owner | review_by | status | decided_by | side |
|---|---|---|---|---|---|---|---|---|---|---|
