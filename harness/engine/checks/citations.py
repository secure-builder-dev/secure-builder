# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Citation verification (spec 01 §8.3). Every citation-shaped token in the
governed document set is resolved against the vendored catalogues:

  unknown identifier            fail — typo, invented, or from another framework
  withdrawn identifier          fail, naming its replacement
  superseded publication rev.   report, naming the current revision
  revision never published      fail, listing what was published
  stale edition numbering       fail, naming the identifier and the title it now carries
  platform not in the index     report, not fail, with a path to supply it

A deliberate mention of a withdrawn identifier is allowed on a line marked
`(withdrawn)` or `engine:historical`. Prose that resembles an identifier — a
ticket number, a version — is not misread: control identifiers are recognised
only for the families the catalogue declares.
"""
import re

from .. import catalogue
from ..outcome import Outcome
from .reference_integrity import governed_documents

NAME = "citations"
HISTORICAL = re.compile(r"\(withdrawn\)|engine:historical", re.I)
PUBLICATION = re.compile(r"\b(?:NIST\s+)?(SP\s*800-\d+[A-Z]?)(?:\s*,?\s*(?:Rev(?:ision)?\.?\s*(\d+)))?", re.I)
FIPS = re.compile(r"\bFIPS\s*(\d+-\d)\b")
OWASP = re.compile(r"\bOWASP\s+(MASVS(?:-[A-Z]+)?|ASVS|Top\s*10)\b(?:[:\s]*(\d{4}))?", re.I)
TOP10_ITEM = re.compile(r"\b(A\d{1,2})(?::(\d{4}))?\b")


def control_pattern(families):
    return re.compile(r"(?<![\w-])(" + "|".join(sorted(families)) + r")-(\d+)(?:\((\d+)\))?(?![\w-])")


def verify_text(text, cats, accepted_unindexed=()):
    """(failures, reports) for one document's text. Platforms the project has declared
    unindexed (a recorded acceptance in its configuration) are counted, not re-reported."""
    failures, reports = [], []
    accepted = {p.upper() for p in accepted_unindexed}
    ctrl = cats.get("nist-sp-800-53-r5")
    pubs = cats.get("publications")
    top10 = cats.get("owasp-top10")
    pat = control_pattern(ctrl.get("families", [])) if ctrl else None
    for n, line in enumerate(text.splitlines(), 1):
        historical = bool(HISTORICAL.search(line))
        if pat:
            for m in pat.finditer(line):
                ident = f"{m.group(1)}-{m.group(2)}"
                e = ctrl["entries"].get(ident)
                if e is None:
                    if ctrl.get("coverage", "").startswith("seed"):
                        reports.append(f"line {n}: {ident} is not in the seed catalogue — ingest the full catalogue to resolve it")
                    else:
                        failures.append(f"line {n}: {ident} is unknown — typo, invented, or from another framework")
                elif e["status"] == "withdrawn" and not historical:
                    failures.append(f"line {n}: {ident} is withdrawn — replaced by {', '.join(e.get('superseded_by', []))}")
        for m in PUBLICATION.finditer(line):
            key = "NIST " + re.sub(r"\s+", " ", m.group(1).upper()).replace("SP800", "SP 800")
            rev = m.group(2)
            e = pubs["entries"].get(key) if pubs else None
            if e is None:
                reports.append(f"line {n}: {key} is not in the publication index — supply it with `catalogue ingest`")
                continue
            if rev:
                r = f"Rev {rev}"
                if r not in e.get("published_revisions", []):
                    failures.append(f"line {n}: {key} {r} was never published — published: {', '.join(e.get('published_revisions', []))}")
                elif r != e.get("current_revision"):
                    reports.append(f"line {n}: {key} {r} is superseded — current revision is {e.get('current_revision')}")
        for m in FIPS.finditer(line):
            key = f"FIPS {m.group(1)}"
            e = pubs["entries"].get(key) if pubs else None
            if e is None:
                reports.append(f"line {n}: {key} is not in the publication index")
            elif e["status"] == "withdrawn" and not historical:
                failures.append(f"line {n}: {key} is withdrawn — replaced by {', '.join(e.get('superseded_by', []))}")
        for m in OWASP.finditer(line):
            platform = m.group(1).upper().replace(" ", "")
            if platform.startswith("MASVS") or platform == "ASVS":
                if "owasp-" + platform.split("-")[0].lower() not in cats:
                    if platform.split("-")[0] in accepted:
                        verify_text.accepted_count = getattr(verify_text, "accepted_count", 0) + 1
                    else:
                        reports.append(f"line {n}: OWASP {platform} is on a platform not in the index — supply its catalogue with `catalogue ingest`")
            elif platform == "TOP10" and top10:
                edition = m.group(2)
                for im in TOP10_ITEM.finditer(line):
                    num = im.group(1).upper()
                    num = "A" + num[1:].zfill(2)
                    ed = im.group(2) or edition
                    cur = top10["entries"].get(num)
                    if ed and ed != top10.get("revision") and cur:
                        failures.append(f"line {n}: OWASP Top 10 {im.group(1)}:{ed} uses stale edition numbering — {num} now carries the title '{cur['title']}' ({top10['revision']})")
                    elif cur is None:
                        failures.append(f"line {n}: OWASP Top 10 {num} is not an entry of the {top10.get('revision')} list")
    return failures, reports


def run(root, cfg):
    try:
        cats = catalogue.load_all(root)
    except catalogue.CatalogueError as e:
        return Outcome.could_not_run(NAME, str(e))
    if not cats:
        return Outcome.could_not_run(NAME, "no vendored catalogues under .engine/rules/catalogues — nothing to resolve against is not a pass")
    docs = governed_documents(root, cfg)
    if not docs:
        return Outcome.could_not_run(NAME, "the governed document set resolved to zero documents")
    failures, reports, cited = [], [], 0
    accepted = list((cfg.get("citation_platforms_unindexed") if cfg else None) or [])
    verify_text.accepted_count = 0
    for doc in docs:
        text = doc.read_text(encoding="utf-8", errors="replace")
        f, r = verify_text(text, cats, accepted)
        rel = doc.relative_to(root).as_posix()
        failures += [f"{rel}: {x}" for x in f]
        reports += [f"{rel}: {x}" for x in r]
        cited += len(re.findall(r"\b[A-Z]{2}-\d+\b|SP\s*800-\d+|FIPS\s*\d+-\d|OWASP", text))
    if failures:
        return Outcome.found(NAME, f"{len(failures)} citation(s) fail to resolve; {len(reports)} reported", failures + reports, blocking=True)
    if reports:
        return Outcome.found(NAME, f"{len(reports)} citation(s) reported (superseded revision or platform not indexed); none fail", reports, blocking=False)
    if cited == 0:
        return Outcome.nothing_yet(NAME, "citation-shaped tokens in the governed documents", f"{len(docs)} governed documents cite no standard")
    note = (f"; {verify_text.accepted_count} citation(s) on platform(s) the project declares unindexed ({', '.join(accepted)}) — a recorded acceptance"
            if verify_text.accepted_count else "")
    return Outcome.clean(NAME, f"{cited} citation-shaped token(s) across {len(docs)} governed documents all resolve to real, current entries{note}")
