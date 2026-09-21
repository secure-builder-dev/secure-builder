# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Control-shape detection — one definition, two uses (spec 01 REQ-6.3.1, REQ-7.5.2).

A change or a file is *control-shaped* when it touches authentication,
authorization, audit, redaction, cryptography or scoping code. The gate uses
this on a diff to decide whether the completeness review triggers; the
manifest completeness probe uses it on the tree to find undeclared controls.
Using one definition means the two cannot drift into disagreeing about what a
control is.
"""
import re

FAMILIES = {
    "authentication": re.compile(r"(?i)\b(authenticat\w*|(?:\w+_)?auth(?!oriz)\w*|login|logout|session\w*|jwt|token\w*|passw(or)?d\w*|credential\w*|oauth|oidc|saml|mfa|verify_?token|bearer)\b"),
    "authorization": re.compile(r"(?i)\b(authoriz\w*|permission\w*|role\w*|rbac|abac|acl|can_\w+|is_admin|require_?\w*(role|perm|auth)\w*|policy\w*|entitle\w*|allow\w*|deny\w*)\b"),
    "audit": re.compile(r"(?i)\b(audit\w*|access_?log\w*|event_?log\w*|tamper\w*|append_?only)\b"),
    "redaction": re.compile(r"(?i)\b(redact\w*|sanitiz\w*|mask\w*|scrub\w*|anonymi[sz]\w*|pii)\b"),
    "cryptography": re.compile(r"(?i)\b(crypt\w*|cipher\w*|hash\w*|hmac|sha\d*|aes|rsa|sign\w*|verify_?signature|kms|key_?(ring|store|vault)|tls|ssl|fips)\b"),
    "scoping": re.compile(r"(?i)\b(scope\w*|tenant\w*|owner\w*|ownership|row_?level|multi_?tenant|filter_?by_?(user|tenant|owner|org)\w*|for_?user|isolation)\b"),
}
DEFINITION = re.compile(r"^\s*(?:export\s+)?(?:async\s+)?(?:def|function|class|const|let|var|fun|func)\s+([A-Za-z_]\w*)|"
                        r"^[ \t]*(?!(?:raise|return|throw|new|await|yield|if|elif|else|while|for|assert|del|print|import|from|not|and|or|in|is|case|switch|typeof)\b)"
                        r"(?:(?:public|private|protected|static)\s+)*[\w<>\[\]]+\s+([A-Za-z_]\w*)\s*\(", re.M)
SOURCE_EXT = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".kt", ".java", ".go", ".rb", ".rs", ".cs"}
TEST_PATH = re.compile(r"(^|/)(tests?|spec|__tests__|selftest|fixtures?|mocks?)/|[._-]test\.|_test\.py$|\.spec\.|test_\w+\.py$")


def families_in(text):
    """Which control families a piece of text (a file, a diff hunk, a symbol name) touches."""
    return sorted(name for name, pat in FAMILIES.items() if pat.search(text))


def is_control_shaped(text):
    return bool(families_in(text))


def control_symbols(path, text):
    """(symbol, line, families) for each definition in a file whose name or
    surrounding line reads as a control."""
    out = []
    for m in DEFINITION.finditer(text):
        name = m.group(1) or m.group(2)
        if not name:
            continue
        line_no = text.count("\n", 0, m.start()) + 1
        line = text[m.start():text.find("\n", m.start()) if text.find("\n", m.start()) >= 0 else len(text)]
        fams = families_in(name) or families_in(line)
        if fams:
            out.append((name, line_no, fams))
    return out


def diff_is_control_shaped(diff_text):
    """Control-shaped if any added or removed line, or any touched file's path, reads as a control."""
    touched = []
    for line in diff_text.splitlines():
        if line.startswith(("+++ ", "--- ")):
            touched.append(line[4:].strip())
        elif line.startswith(("+", "-")) and not line.startswith(("+++", "---")):
            touched.append(line[1:])
    fams = set()
    for t in touched:
        fams.update(families_in(t))
    return sorted(fams)
