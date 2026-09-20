# © 2026 Casey Houle. All rights reserved.
"""The four ownership classes (spec 06 §2). This list is the contract.

Every path the harness places in a project belongs to exactly one class, and
the class is declared here — never inferred from a path's location or contents.
A human can read each class in one screen. Project-owned paths are enumerated
too, although the update performs no action on them: an unlisted path is
indistinguishable from an oversight.

Paths are relative to the project root. A trailing slash names a directory
whose entire contents belong to the class. Sources are relative to the
harness's own tree (engine/dist/ for documents, engine/ for the package).
"""

ENGINE_DIR = ".engine"

# Overwritten unconditionally on every update. Local edits are discarded, with
# the prior content preserved beside the file under BACKUP_SUFFIX and reported.
ENGINE_OWNED = {
    f"{ENGINE_DIR}/harness/engine/": "engine/",               # the checks, the scripts, the package
    f"{ENGINE_DIR}/harness/selftest/": "selftest/",          # the self-test suite
    f"{ENGINE_DIR}/harness/run.py": "engine/dist/run.py",    # the entrypoint a project invokes
    f"{ENGINE_DIR}/rules/RULES.md": "engine/dist/rules/RULES.md",   # the rulebook (imported)
    f"{ENGINE_DIR}/agents/": "engine/dist/agents/",          # reviewer definitions, whole, tracked
    f"{ENGINE_DIR}/hooks/": "engine/dist/hooks/",            # pre-execution hooks
    f"{ENGINE_DIR}/CHANGES.md": "engine/dist/CHANGES.md",    # what an update newly fails (REQ-6.6)
    f"{ENGINE_DIR}/.gitignore": "engine/dist/gitignore",      # what stays out of version control (spec 02 §2)
}

# Written only when missing; never touched again.
SEED_IF_ABSENT = {
    "AGENTS.md": "engine/dist/templates/AGENTS.md",                    # project instruction file (import + project rules)
    f"{ENGINE_DIR}/control-manifest.json": "engine/dist/templates/control-manifest.json",
    f"{ENGINE_DIR}/records/gate-log.md": "engine/dist/templates/records/gate-log.md",
    f"{ENGINE_DIR}/records/findings-register.md": "engine/dist/templates/records/findings-register.md",
    f"{ENGINE_DIR}/records/governance-changelog.md": "engine/dist/templates/records/governance-changelog.md",
    f"{ENGINE_DIR}/records/carried-findings.md": "engine/dist/templates/records/carried-findings.md",
    f"{ENGINE_DIR}/records/standing-state-deltas.md": "engine/dist/templates/records/standing-state-deltas.md",
    f"{ENGINE_DIR}/records/reconciliation-obligations.md": "engine/dist/templates/records/reconciliation-obligations.md",
    f"{ENGINE_DIR}/records/high-side-changes.md": "engine/dist/templates/records/high-side-changes.md",
    f"{ENGINE_DIR}/records/ingest-records.md": "engine/dist/templates/records/ingest-records.md",
    f"{ENGINE_DIR}/records/README.md": "engine/dist/templates/records/README.md",
}

# Written beside the project's copy under REFERENCE_SUFFIX; never read by a check.
# Kept deliberately small: documents whose structure is the engine's and whose
# content is the project's.
ENGINE_REFERENCE = {
    "AGENTS.md": "engine/dist/templates/AGENTS.md",
    f"{ENGINE_DIR}/control-manifest.json": "engine/dist/templates/control-manifest.json",
    f"{ENGINE_DIR}/records/gate-log.md": "engine/dist/templates/records/gate-log.md",
}

# Never written, never deleted, under any circumstance.
PROJECT_OWNED = [
    f"{ENGINE_DIR}/config.json",          # project configuration (written once by init, never by update)
    f"{ENGINE_DIR}/records/",             # every record the project produces
    f"{ENGINE_DIR}/local/",               # per-clone runtime state (snapshots)
    f"{ENGINE_DIR}/scan/",                # scan artifacts
    f"{ENGINE_DIR}/catalogues/",          # vendored standards catalogues and their pins
    f"{ENGINE_DIR}/VERSION",              # written by the update itself, but it records the project's state
    "plans/",
    "tickets/",
    "src/",
]

ENGINE_OWNED_MARKER = "ENGINE-OWNED: local edits to this file are discarded on update"
BACKUP_SUFFIX = ".pre-update"
REFERENCE_SUFFIX = ".engine-reference"
TRACKING_RECORD = f"{ENGINE_DIR}/agents/.placed"
VERSION_FILE = f"{ENGINE_DIR}/VERSION"
PLACED_MANIFEST = f"{ENGINE_DIR}/placed.json"   # every engine-owned file placed, with its hash


def classes():
    """The enumeration, as (class name, mapping-or-list)."""
    return [("engine-owned", ENGINE_OWNED), ("seed-if-absent", SEED_IF_ABSENT),
            ("engine-reference", ENGINE_REFERENCE), ("project-owned", PROJECT_OWNED)]


def class_of(path):
    """Which class a project path belongs to, or None. Project-owned wins over a
    seed target only for paths the seed never touches after first write."""
    for name, table in classes():
        keys = table if isinstance(table, list) else list(table)
        for k in keys:
            if path == k or (k.endswith("/") and path.startswith(k)):
                if name == "engine-reference":
                    continue      # reference copies live under a suffix; the bare path is seed/project
                return name
    return None
