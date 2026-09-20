#!/usr/bin/env python3
# © 2026 Casey Houle. All rights reserved.
"""progress — evaluates v1.0.md. Human-owned; in the build's governance set.

Exit 0 means v1.0 is reached. Anything else means it is not, and the output
says which clause failed and why. Every clause is recomputed from the tree;
the ledger's own claims are never trusted (spec 07 §6).

The empty case fails. A ledger with no rows, a specs directory with no
requirements, or a receipt with no sections is a failure, never a pass
(spec 05 §7.2).

Flags:
  --root DIR      evaluate a different tree (used by the negative fixtures)
  --quiet         print only the verdict line
  --count-done    print the number of done rows and exit 0 (stall detector)
  --spend-check   exit 1 if .journal/heads has more lines than budget.txt allows
  --no-check      skip clauses 3, 4 and 7 (the ones that run the harness)
  --no-reset      report drift but do not reset drifted rows to todo
  --drift-only    exit 1 only for rows claiming done falsely (clause 2/5);
                  todo/doing rows are fine. Used by the pre-commit hook.
"""
import json
import pathlib
import re
import subprocess
import sys

STATUSES = ("todo", "doing", "done", "defer", "na")
GOVERNED_SPECS = ("01", "02", "03", "04", "05", "06", "11")
REQ_LINE = re.compile(r"^\*\*(REQ-[0-9]+(?:\.[0-9]+)*[a-z]?)\*\*")
FAIL_MARK = re.compile(r"(\bFAIL\b|\bexit [1-9][0-9]*\b)")
PASS_MARK = re.compile(r"\bexit 0\b")
BROKEN_HDR = "--- output with the property broken"
RESTORED_HDR = "--- output with the property restored"
COLUMNS = ["req", "spec", "stage", "status", "impl", "receipt", "note"]


class Failure(Exception):
    pass


def spec_requirements(root):
    """(spec, req) for every numbered requirement in the governed specs."""
    specs = root / "specs"
    found = set()
    for path in sorted(specs.glob("*.md")) if specs.is_dir() else []:
        no = path.name[:2]
        if no not in GOVERNED_SPECS:
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            m = REQ_LINE.match(line)
            if m:
                found.add((no, m.group(1)))
    if not found:
        raise Failure("clause 1: no requirements found under specs/ — nothing to measure is not done")
    return found


def read_ledger(root):
    path = root / "ledger.tsv"
    if not path.is_file():
        raise Failure("clause 1: ledger.tsv is missing")
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].split("\t") != COLUMNS:
        raise Failure(f"clause 1: ledger.tsv header must be {COLUMNS}")
    rows = []
    for n, line in enumerate(lines[1:], start=2):
        if not line.strip():
            continue
        cells = line.split("\t")
        if len(cells) != len(COLUMNS):
            raise Failure(f"clause 1: ledger.tsv line {n} has {len(cells)} columns, expected {len(COLUMNS)}")
        rows.append(dict(zip(COLUMNS, cells)))
    if not rows:
        raise Failure("clause 1: ledger.tsv has no rows — an empty ledger is not a finished build")
    return rows


def write_ledger(root, rows):
    with (root / "ledger.tsv").open("w", encoding="utf-8", newline="\n") as f:
        f.write("\t".join(COLUMNS) + "\n")
        for r in rows:
            f.write("\t".join(r[c] for c in COLUMNS) + "\n")


def check_receipt(root, row):
    """Return None if the receipt proves the check was observed failing, else a reason."""
    rpath = row["receipt"]
    if rpath in ("", "-"):
        return "no receipt recorded"
    receipt = root / rpath
    if not receipt.is_file():
        return f"receipt {rpath} does not exist"
    text = receipt.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        return f"receipt {rpath} is empty"
    fields = {}
    for line in text.splitlines():
        m = re.match(r"^(REQ|CHECK|MUTATION):\s*(.*)$", line)
        if m and m.group(1) not in fields:
            fields[m.group(1)] = m.group(2).strip()
    for key in ("REQ", "CHECK", "MUTATION"):
        if not fields.get(key):
            return f"receipt {rpath} has no {key}: line"
    if fields["REQ"] != row["req"]:
        return f"receipt {rpath} names {fields['REQ']}, row is {row['req']}"
    if not (root / fields["CHECK"]).exists():
        return f"receipt {rpath} CHECK path {fields['CHECK']} does not exist"
    for bad in ("delete", "remove", "rename", "rm "):
        if re.search(r"\b" + re.escape(bad), fields["MUTATION"], re.I):
            return (f"receipt {rpath} MUTATION reads as a removal ('{bad.strip()}'), "
                    "not a property-level alteration (spec 07 §2.2)")
    b = text.find(BROKEN_HDR)
    r = text.find(RESTORED_HDR)
    if b < 0 or r < 0:
        return f"receipt {rpath} lacks a broken and/or restored section"
    if r < b:
        return f"receipt {rpath} has the restored section before the broken one"
    broken = text[text.index("\n", b) + 1:r] if "\n" in text[b:r] else ""
    restored = text[text.index("\n", r) + 1:] if "\n" in text[r:] else ""
    if not broken.strip():
        return f"receipt {rpath} broken section is empty"
    if not restored.strip():
        return f"receipt {rpath} restored section is empty"
    if not FAIL_MARK.search(broken):
        return f"receipt {rpath} broken section shows no failure — the mutation did not break the check"
    if not PASS_MARK.search(restored):
        return f"receipt {rpath} restored section shows no 'exit 0'"
    if re.search(r"\bFAIL\b", restored):
        return f"receipt {rpath} restored section still shows FAIL"
    return None


def clause_1_and_2(root, rows, reset):
    problems = []
    expected = spec_requirements(root)
    have = {(r["spec"], r["req"]) for r in rows}
    for key in sorted(expected - have):
        problems.append(f"clause 1: {key[0]}/{key[1]} has no ledger row")
    for key in sorted(have - expected):
        problems.append(f"clause 1: ledger row {key[0]}/{key[1]} matches no requirement in specs/")
    if len(have) != len(rows):
        problems.append("clause 1: duplicate (spec, req) rows in ledger")

    drifted = []
    for r in rows:
        tag = f"{r['spec']}/{r['req']}"
        st = r["status"]
        if st not in STATUSES:
            problems.append(f"clause 1: {tag} has status '{st}', not one of {STATUSES}")
            continue
        if st in ("todo", "doing"):
            problems.append(f"clause 1: {tag} is still {st}")
        elif st == "na" and not r["note"].strip():
            problems.append(f"clause 1: {tag} is na with no reason")
        elif st == "defer":
            if not r["note"].strip():
                problems.append(f"clause 1: {tag} is defer with no reason")
            elif not re.search(r"\bv1\.[0-9]+\b", r["note"]):
                problems.append(f"clause 1: {tag} is defer with no version tag (v1.x)")
        elif st == "done":
            reasons = []
            impls = [p.strip() for p in r["impl"].split(";") if p.strip()]
            if not impls or impls == ["-"]:
                reasons.append("no impl pointer")
            for p in impls:
                if p == "-" or not (root / p).exists():
                    reasons.append(f"impl {p} does not exist")
            rr = check_receipt(root, r)
            if rr:
                reasons.append(rr)
            if reasons:
                drifted.append((r, reasons))
        if r["impl"].strip().lower() == "unknown":
            problems.append(f"clause 5: {tag} impl reads 'unknown'")

    for r, reasons in drifted:
        tag = f"{r['spec']}/{r['req']}"
        for why in reasons:
            problems.append(f"clause 2: {tag} marked done but {why}")
        if reset:
            r["status"] = "todo"
            r["note"] = ("drift: " + "; ".join(reasons) + (" | " + r["note"] if r["note"] else ""))[:400]
    if drifted and reset:
        write_ledger(root, rows)
        problems.append(f"clause 2: {len(drifted)} drifted row(s) reset to todo (spec 07 §6)")
    return problems


def run(root, *args):
    return subprocess.run([sys.executable, *args], cwd=str(root), capture_output=True, text=True)


def clause_3_4(root):
    problems = []
    res = run(root, "-m", "engine", "check", "--json")
    if res.returncode != 0:
        tail = (res.stdout + res.stderr).strip().splitlines()[-3:]
        problems.append(f"clause 3: `python -m engine check` exited {res.returncode}: " + " | ".join(tail))
    summary = None
    for line in res.stdout.splitlines():
        if line.startswith("{"):
            try:
                summary = json.loads(line)
            except ValueError:
                pass
    if summary is None:
        problems.append("clause 4: check output carried no JSON summary line")
        return problems
    st = summary.get("selftest")
    if not isinstance(st, dict) or not all(k in st for k in ("pass", "fail", "skip")):
        problems.append("clause 4: check summary has no selftest {pass, fail, skip}")
        return problems
    if st["pass"] == 0:
        problems.append("clause 4: self-test suite passed zero cases — an unrun suite is an absent suite")
    if st["fail"]:
        problems.append(f"clause 4: self-test suite reports {st['fail']} failure(s)")
    if st["skip"]:
        named = named_skips(root)
        for name in st.get("skips", []) or ["<unnamed>"] * st["skip"]:
            if name not in named:
                problems.append(f"clause 4: skip '{name}' is not named in v1.0.md")
    return problems


def named_skips(root):
    text = (root / "v1.0.md").read_text(encoding="utf-8") if (root / "v1.0.md").is_file() else ""
    if "## Named skips" not in text:
        return set()
    block = text.split("## Named skips", 1)[1]
    return {ln.strip("- ").strip() for ln in block.splitlines() if ln.strip().startswith("-")}


def clause_6(root):
    p = root / "LIFECYCLE-EXERCISE.md"
    if not p.is_file():
        return ["clause 6: LIFECYCLE-EXERCISE.md does not exist — the lifecycle has not been exercised"]
    t = p.read_text(encoding="utf-8")
    out = []
    if not re.search(r"\b20[0-9]{2}-[0-9]{2}-[0-9]{2}\b", t):
        out.append("clause 6: LIFECYCLE-EXERCISE.md has no date")
    if re.search(r"<[^>]+>|\bTODO\b|\bTBD\b", t):
        out.append("clause 6: LIFECYCLE-EXERCISE.md still contains template placeholders")
    if not re.search(r"\b[0-9a-f]{7,40}\.\.[0-9a-f]{7,40}\b", t):
        out.append("clause 6: LIFECYCLE-EXERCISE.md names no commit range")
    return out


def clause_7(root):
    res = run(root, "-m", "engine", "degradation")
    if res.returncode != 0:
        return [f"clause 7: `python -m engine degradation` exited {res.returncode}"]
    if not res.stdout.strip():
        return ["clause 7: degradation statement is empty"]
    return []


def clause_8(root):
    p = root / "RELEASE-RECORD.md"
    if not p.is_file():
        return ["clause 8: RELEASE-RECORD.md does not exist"]
    t = p.read_text(encoding="utf-8").lower()
    if "integration tier: not verified in this environment" in t:
        return []
    if re.search(r"integration tier: passed \(environment: [^)\n]+\)", t):
        return []
    return ["clause 8: RELEASE-RECORD.md records neither a passed integration tier with its "
            "environment nor 'not verified in this environment'"]


def main(argv):
    args = set(argv)
    root = pathlib.Path(".").resolve()
    if "--root" in argv:
        root = pathlib.Path(argv[argv.index("--root") + 1]).resolve()
    quiet = "--quiet" in args

    if "--count-done" in args:
        try:
            rows = read_ledger(root)
        except Failure:
            print(0)
            return 0
        print(sum(1 for r in rows if r["status"] == "done"))
        return 0

    if "--spend-check" in args:
        budget = root / "budget.txt"
        heads = root / ".journal" / "heads"
        if not budget.is_file():
            print("spend-check: budget.txt missing — no ceiling is set, refusing to run unbounded")
            return 1
        cap = int(budget.read_text().strip().split()[0])
        used = len(heads.read_text().splitlines()) if heads.is_file() else 0
        print(f"spend-check: {used} iterations of {cap}")
        return 0 if used < cap else 1

    problems = []
    rows = []
    try:
        rows = read_ledger(root)
        drift_only = "--drift-only" in args
        problems += clause_1_and_2(root, rows, reset=not drift_only and "--no-reset" not in args)
        if drift_only:
            drift = [p for p in problems if p.startswith(("clause 2:", "clause 5:"))]
            for p in drift:
                print(p)
            tags = {p.split(" ")[2] for p in drift}
            print(f"drift-only: {len(tags)} row(s) claim done falsely" if drift
                  else f"drift-only: no drift in {sum(1 for r in rows if r['status'] == 'done')} done row(s)")
            return 1 if drift else 0
        if "--no-check" not in args:
            problems += clause_3_4(root)
        problems += clause_6(root)
        if "--no-check" not in args:
            problems += clause_7(root)
        problems += clause_8(root)
    except Failure as e:
        problems.append(str(e))

    if not quiet:
        for p in problems:
            print(p)
    done = sum(1 for r in rows if r["status"] == "done")
    if problems:
        by = {}
        for p in problems:
            by[p.split(":")[0]] = by.get(p.split(":")[0], 0) + 1
        print(f"progress: NOT v1.0 — {len(problems)} problem(s): " +
              ", ".join(f"{k} x{v}" for k, v in sorted(by.items())))
        return 1
    print(f"progress: v1.0 REACHED — {done} requirements done, all clauses satisfied")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
