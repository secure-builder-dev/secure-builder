# Governance changelog

© 2026 Casey Houle. All rights reserved.

One row per change to the rule set, written before the commit. The sign-off
records what the human was shown. This is the harness's configuration change
control record.

Schema: governance-changelog/1.

| date | change_id | file_section | base_commit | result_commit | grounding | sign_off | retroactive | rode_along | side |
|---|---|---|---|---|---|---|---|---|---|
| 2026-10-10T02:56:18+00:00 | GOV-1 | .engine/rules/control-manifest.json controls, .engine/rules/dependency-policy.json dependencies | 32ffefcdf605 | pending | [finding: honey-do TK-1 gate prepare run 3, manifest-entry and dependency-policy] | Casey Houle approved after being shown the literal text: "- "id": "CTRL-EXAMPLE", - "placeholder": true, - "description": "Replace this placeholder with a real control. A manifest holding only placeholders is reported as template-only, never as passing.", - "location": {"file": "src/example.py", "symbol": "require_auth"}, + "id": "CTRL-AUTHN-BEARER", + "description": "Every /api route identifies the caller from Authorization: Bearer <token>, compared wit" | no | - | local |
