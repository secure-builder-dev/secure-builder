# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""The security-gate checklist as data (spec 01 §6.2–6.5, §2.3).

Everything the reviewing agent is asked lives here, once: the base checklist,
the conditional blocks with their activation semantics (additive, substitutive,
informational) and the external standard each conditional check cites, the
completeness-review questions, and the verdict block. The reviewer definition
under engine/dist/agents is rendered from this module, so the two cannot
drift; the verdict block is duplicated into the reference document and the
doc-consistency check asserts the copies agree (REQ-6.5.2).

The checklist version is a content digest of this data (spec 01 REQ-1.5.1):
what the reviewer was asked is re-derivable even though its answer is not.
"""
import hashlib
import json

BASE = [
    ("B1", "Credential hygiene", "No embedded secrets, including no fallback or default values in configuration."),
    ("B2", "Authentication completeness", "Every endpoint requires a valid token, with enumerated exceptions; the authenticating "
           "middleware is registered before all handlers such that no route can be reached around it."),
    ("B3", "Authorization enforcement", "Role and scope rules are enforced at the API layer, never only in the client."),
    ("B4", "Negative coverage", "Tests exist for the rejection cases, not only the success cases."),
    ("B5", "Last-privileged-principal guard", "Removal of the last privileged principal is prevented server-side."),
    ("B6", "Injection defence", "Parameterized queries only."),
    ("B7", "Soft-delete and archival filters", "Applied to all active-record queries where the schema defines them."),
    ("B8", "Error handling", "A global handler prevents stack traces, internal messages, database errors, file paths "
           "and storage keys from reaching responses."),
    ("B9", "Upload handling", "Where uploads exist, no untrusted writes to local disk."),
    ("B10", "Dependency policy", "Every new dependency is recorded in the project's dependency policy document with its "
            "approval state and the date it became available on the target environment. Where the target requires "
            "approval and transfer before use, an unapproved dependency is a blocking finding, and the finding names "
            "the lead time."),
    ("B11", "Project-specific invariants", "The project's own named invariants (AGENTS.md, Project rules) are enforced "
            "without being asked for each time."),
]

# Conditional blocks: (id, title, activates when, semantics, replaces, [(check, standard citation)])
# Semantics: additive runs in addition to the base set; substitutive replaces a named
# subset (only infrastructure-shaped checks are substitutable; application-layer checks
# never are); informational is displayed but not enforced.
INFRA_CLOUD = ["I1", "I2", "I3"]
CONDITIONAL = [
    ("ELEVATED", "Elevated-tier block", {"tier": "IL6"}, "additive", [], [
        ("Validated cryptographic modules only, with named prohibited algorithms", "FIPS 140-3; NIST SP 800-53 SC-13"),
        ("Response classification marking", "NIST SP 800-53 AC-16"),
        ("No unclassified external calls at runtime", "NIST SP 800-53 SC-7, CA-3"),
        ("Audit logs written to append-only storage not writable by the application process", "NIST SP 800-53 AU-9"),
        ("Cross-domain boundaries documented", "NIST SP 800-53 AC-4, SC-7"),
        ("Personnel clearance data delegated to the identity provider, never stored in the application database", "NIST SP 800-53 AC-2, PS-3"),
    ]),
    ("MOBILE", "Mobile-track block", {"track": "android"}, "additive", [], [
        ("Transport security minimums with no cleartext permitted", "NIST SP 800-53 SC-8; NIST SP 800-163"),
        ("No sensitive data on shared external storage", "NIST SP 800-163; OWASP MASVS-STORAGE"),
        ("No sensitive data in platform logs", "OWASP MASVS-STORAGE"),
        ("Credential storage in the platform keystore rather than preference files", "OWASP MASVS-STORAGE; NIST SP 800-53 IA-5"),
        ("Authenticated backend calls", "NIST SP 800-53 IA-2; OWASP MASVS-AUTH"),
        ("Certificate pinning evaluated, with justified absence permitted", "OWASP MASVS-NETWORK"),
        ("No embedded credentials or endpoints in source", "NIST SP 800-53 IA-5; OWASP MASVS-STORAGE"),
        ("Exported inter-process components minimized, with per-component justification", "OWASP MASVS-PLATFORM"),
        ("A documented minimum platform version supporting the above", "OWASP MASVS-PLATFORM"),
    ]),
    ("ONPREM", "On-prem provider block", {"provider": "tactical"}, "substitutive", INFRA_CLOUD, [
        ("Transport termination and cipher minimums at the proxy layer", "NIST SP 800-52; NIST SP 800-53 SC-8"),
        ("No plaintext secrets in provisioned configuration", "NIST SP 800-53 IA-5, SC-28"),
        ("Audit log destination and retention", "NIST SP 800-53 AU-4, AU-11"),
        ("Encryption at rest for persistent storage", "NIST SP 800-53 SC-28"),
        ("Firewall rules with no management ports exposed to the client network segment", "NIST SP 800-53 SC-7"),
        ("Current OS and runtime packages", "NIST SP 800-53 SI-2"),
        ("Documented deployment authorization", "NIST SP 800-53 CA-6"),
    ]),
]
CLOUD_INFRA = [
    ("I1", "Cloud infrastructure: managed transport termination and cipher policy", "NIST SP 800-53 SC-8"),
    ("I2", "Cloud infrastructure: secrets held in the provider's secrets service, not configuration", "NIST SP 800-53 IA-5"),
    ("I3", "Cloud infrastructure: audit log destination and retention configured", "NIST SP 800-53 AU-4, AU-11"),
]

COMPLETENESS = [
    ("Q1", "Does the guard recurse into nested structures, or inspect only top-level keys?"),
    ("Q2", "Is there a second write path to this same state, and is the guard on both?"),
    ("Q3", "Which framework entry points does this hook NOT cover? Enumerate them."),
    ("Q4", "What does this verification NOT verify? Enumerate it."),
    ("Q5", "Name the production call site — file and line."),
    ("Q6", "If it rejects input: is the schema strict, and is it actually mounted?"),
]
ENUMERATE = ("Q3", "Q4")

VERDICT_FIELDS = [
    "verdict", "tier", "run", "range", "control_shaped", "manifest_result", "completeness_blocks",
    "platform_surface", "scan_verdict", "open_findings", "blocking_findings", "tickets_opened",
    "reviewer_class", "model", "attested_by", "checklist_version", "harness_version",
]


def activation(cfg):
    """Which conditional blocks are active, substitutive, or informational for a shape."""
    out = []
    for bid, title, when, semantics, replaces, checks in CONDITIONAL:
        axis, value = next(iter(when.items()))
        active = getattr(cfg, axis, None) == value if cfg else False
        if active:
            out.append((bid, semantics))
        elif bid == "ELEVATED":
            out.append((bid, "informational"))
    return out


def compose(cfg):
    """The checklist for a shape: base, cloud infrastructure unless substituted, active
    blocks. Application-layer checks are never removed (REQ-2.3.3)."""
    items = [("base", i, t, d, None) for i, t, d in BASE]
    acts = dict(activation(cfg))
    substituted = set()
    for bid, sem in acts.items():
        if sem == "substitutive":
            substituted.update(next(b[4] for b in CONDITIONAL if b[0] == bid))
    items += [("infra", i, t, None, s) for i, t, s in CLOUD_INFRA if i not in substituted]
    for bid, title, when, semantics, replaces, checks in CONDITIONAL:
        sem = acts.get(bid)
        if sem is None:
            continue
        for n, (check, std) in enumerate(checks, 1):
            items.append((f"{bid}:{sem}", f"{bid}{n}", check, None, std))
    return items


def version():
    """Content digest of everything the reviewer is asked."""
    payload = json.dumps({"base": BASE, "conditional": CONDITIONAL, "cloud": CLOUD_INFRA,
                          "completeness": COMPLETENESS, "verdict": VERDICT_FIELDS}, sort_keys=True)
    return "cl-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def verdict_block_text():
    """The verdict block, defined here and copied verbatim wherever it is shown."""
    lines = ["<!-- engine:block verdict-block -->", "```", "VERDICT"]
    lines += [f"{f}: <value>" for f in VERDICT_FIELDS]
    lines += ["```", "<!-- engine:end verdict-block -->"]
    return "\n".join(lines)


def render_definition():
    """The self-contained security-gate reviewer definition (spec 03 REQ-1.3.1)."""
    L = ["# Security gate", "", "© 2026 Casey Houle. All rights reserved.",
         "ENGINE-OWNED: local edits to this file are discarded on update", "",
         f"Checklist version: {version()}", "",
         "You are the security gate. You run in a fresh session from a generated handoff. You read the",
         "diff from version control at the range the handoff names — never a diff supplied to you. You",
         "do not read the conversation in which the code was written; it is not available to you by design,",
         "and if you have incidental access you do not use it. This definition is self-contained: it",
         "references no other file for its procedure, because a referenced file would not reach you.", "",
         "The quality gate has already passed on this range; if the handoff does not say so, stop.", "",
         "Read at the start: the findings register (Table A rows are checks that must still exist; Table B",
         "rows with unsatisfied proof are reported every run), and the control manifest.", "",
         "## Base checklist — every run", ""]
    L += [f"{i}. **{t}** — {d}" for i, t, d in BASE]
    L += ["", "## Cloud infrastructure — unless the on-prem block substitutes", ""]
    L += [f"{i}. {t} *(cites: {s})*" for i, t, s in CLOUD_INFRA]
    for bid, title, when, semantics, replaces, checks in CONDITIONAL:
        axis, value = next(iter(when.items()))
        L += ["", f"## {title} — {semantics}; active when {axis}={value}"
              + (f"; replaces {', '.join(replaces)} only (application-layer checks are never substituted)" if replaces else "")
              + ("; when inactive it is shown and not enforced" if bid == "ELEVATED" else ""), ""]
        L += [f"{bid}{n}. {c} *(cites: {s})*" for n, (c, s) in enumerate(checks, 1)]
    L += ["", "## Completeness review — only when the diff is control-shaped", "",
          "Control-shaped: the diff creates or modifies authentication, authorization, audit, redaction,",
          "cryptography or scoping code. The handoff says whether it is. When it is, answer the following",
          "in prose, per control touched. A question answered with a checkmark or a bare pass has not been",
          "answered and is a blocking finding. Q3 and Q4 require you to produce a list.", ""]
    L += [f"- **{q}** {text}" for q, text in COMPLETENESS]
    L += ["", "A control-shaped diff with no corresponding manifest entry in the same change is a blocking finding.", "",
          "## Findings", "",
          "A finding is blocking or it is not; there is no severity weighting and no score. Every finding is",
          "dispositioned: mechanical becomes a check, judgment becomes a checklist line.", "",
          "## Verdict block — emit exactly this, filled in, as the last thing you write", "",
          verdict_block_text(), "",
          "reviewer_class is `automated`. model is your own identifier and parameter scale. You never merge,",
          "approve your own work, or override a verdict; the verdict is recorded by the harness and attested",
          "by a named human.", ""]
    return "\n".join(L)


def render_reference():
    return "\n".join(["# Verdict block reference", "", "© 2026 Casey Houle. All rights reserved.",
                      "ENGINE-OWNED: local edits to this file are discarded on update", "",
                      "The verdict block every gate run ends with. This copy and the one in the reviewer",
                      "definition are asserted identical by the doc-consistency check (spec 01 REQ-6.5.2).", "",
                      verdict_block_text(), ""])
