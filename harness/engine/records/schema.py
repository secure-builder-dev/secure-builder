# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Record schemas — defined in exactly one place (spec 02 REQ-3.3.1).

Every record the harness writes is a markdown table whose header must match the
schema here; a check asserts it (REQ-3.3.2). Schemas are versioned, and a file
marks a version boundary explicitly rather than leaving earlier rows in an old
shape unmarked (REQ-3.3.3, REQ-1.5). Every record carries the side that produced
it (spec 04 REQ-10.1.4).
"""

GATE_LOG = ("gate-log", 1, [
    "date", "unit", "range", "run", "mode", "verdict", "findings", "tickets", "reviewer",
    "reviewer_class", "model", "attested_by", "harness_version", "checklist_version", "side",
    "controls", "supersedes", "deferred", "obligation",
])
FINDINGS_A = ("findings-register-a", 1, ["id", "class", "mechanism", "lives_in", "status", "decided_by", "side"])
FINDINGS_B = ("findings-register-b", 1, [
    "id", "risk", "attack_path", "compensating_control", "proof", "re_review_trigger", "owner",
    "review_by", "status", "decided_by", "side",
])
GOVERNANCE = ("governance-changelog", 1, [
    "date", "change_id", "file_section", "base_commit", "result_commit", "grounding", "sign_off",
    "retroactive", "rode_along", "side",
])
CARRIED = ("carried-findings", 1, [
    "id", "component", "version", "severity", "reason_no_fix", "owner", "milestone", "milestone_date",
    "review_by", "status", "status_history", "side",
])
DELTAS = ("standing-state-deltas", 1, ["date", "commit", "measurement", "previous", "current", "disposition", "side"])
OBLIGATIONS = ("reconciliation-obligations", 1, [
    "id", "opened", "unit", "range", "deferred_checks", "declared_by", "reason", "status", "discharged_by_run", "side",
])
DIVERGENCE = ("high-side-changes", 1, ["date", "commit", "what", "why_not_low_side", "authorized_by", "backport_status", "side"])
MUTATION = ("mutation-results", 1, ["date", "control", "branch", "mutation", "baseline", "result", "side"])
INGEST = ("ingest-records", 1, ["date", "bundle", "production_date", "arrival_date", "hash_result", "modified_in_transit", "operator", "side"])

REVIEWER_CLASSES = ("human", "automated", "automated-with-human-review")
VERDICTS = ("pass", "fail", "advisory", "field-pass", "field-fail", "superseded")
MODES = ("normal", "field")
UNKNOWN = "unknown"

ALL = {s[0]: s for s in (GATE_LOG, FINDINGS_A, FINDINGS_B, GOVERNANCE, CARRIED, DELTAS, OBLIGATIONS, DIVERGENCE, INGEST, MUTATION)}

# Which file carries which schema(s), relative to the project root.
FILES = {
    ".engine/records/gate-log.md": ["gate-log"],
    ".engine/records/findings-register.md": ["findings-register-a", "findings-register-b"],
    ".engine/records/governance-changelog.md": ["governance-changelog"],
    ".engine/records/carried-findings.md": ["carried-findings"],
    ".engine/records/standing-state-deltas.md": ["standing-state-deltas"],
    ".engine/records/reconciliation-obligations.md": ["reconciliation-obligations"],
    ".engine/records/high-side-changes.md": ["high-side-changes"],
    ".engine/records/ingest-records.md": ["ingest-records"],
    ".engine/records/mutation-results.md": ["mutation-results"],
}


def header_line(schema):
    return "| " + " | ".join(schema[2]) + " |"


def separator_line(schema):
    return "|" + "---|" * len(schema[2])


def marker_line(schema):
    return f"Schema: {schema[0]}/{schema[1]}."
