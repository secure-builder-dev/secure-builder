# © 2026 Casey Houle. All rights reserved.
"""Generate ledger.tsv from the specs. Run ONCE. Never regenerate over an
existing ledger (spec 07 §7: regeneration silently drops defer/na notes)."""
import re, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SPECS = ROOT / "specs"
OUT = ROOT / "ledger.tsv"
REQ = re.compile(r"^\*\*(REQ-[0-9]+(?:\.[0-9]+)*[a-z]?)\*\*")
SEC = re.compile(r"^##+\s+(\d+)(?:\.(\d+))?")

# (spec, top-level section) -> build stage, from spec 00 §4 plus spec 11.
STAGE = {
    ("01", 1): "3", ("01", 2): "1", ("01", 3): "5", ("01", 4): "9", ("01", 5): "8",
    ("01", 6): "8", ("01", 7): "7", ("01", 8): "10", ("01", 9): "12", ("01", 10): "5",
    ("01", 11): "11", ("01", 12): "6", ("01", 13): "3",
    ("02", 1): "6", ("02", 2): "6", ("02", 3): "6", ("02", 4): "6", ("02", 5): "6",
    ("02", 6): "9", ("02", 7): "12", ("02", 8): "12", ("02", 9): "13", ("02", 10): "14",
    ("02", 11): "6",
    ("03", 1): "8", ("03", 2): "8", ("03", 3): "8", ("03", 4): "8", ("03", 5): "8",
    ("04", 1): "1", ("04", 2): "1", ("04", 3): "10", ("04", 4): "9", ("04", 5): "8",
    ("04", 6): "14", ("04", 7): "14", ("04", 10): "15",
    ("05", 1): "4", ("05", 2): "4", ("05", 3): "4", ("05", 4): "4", ("05", 5): "4",
    ("05", 6): "4", ("05", 7): "4", ("05", 8): "4", ("05", 9): "4", ("05", 10): "4",
    ("06", 1): "2", ("06", 2): "2", ("06", 3): "2", ("06", 4): "2", ("06", 5): "2",
    ("06", 6): "2", ("06", 7): "2", ("06", 8): "14",
    ("11", 1): "14a", ("11", 2): "14a", ("11", 3): "14a", ("11", 4): "14a",
    ("11", 5): "14a", ("11", 6): "14a", ("11", 7): "14a", ("11", 8): "14a",
}
# Refinements where a subsection belongs to a different stage than its parent.
SUB = {("01", "7.5"): "12", ("01", "4.9"): "9", ("01", "4.10"): "13",
       ("05", "6.1"): "9a", ("01", "1.5"): "3"}

def reqs(spec_path, spec_no):
    sec, sub = None, None
    for line in spec_path.read_text(encoding="utf-8").splitlines():
        m = SEC.match(line)
        if m:
            sec = int(m.group(1)); sub = m.group(2)
            continue
        m = REQ.match(line)
        if m and sec is not None:
            key = SUB.get((spec_no, f"{sec}.{sub}")) if sub else None
            stage = key or STAGE.get((spec_no, sec), "?")
            yield m.group(1), stage

def main():
    if OUT.exists() and "--force" not in sys.argv:
        sys.exit("ledger.tsv exists; refusing to regenerate (use --force only on an empty repo)")
    rows = []
    for spec in sorted(SPECS.glob("*.md")):
        no = spec.name[:2]
        if no not in ("01", "02", "03", "04", "05", "06", "11"):
            continue
        for req, stage in reqs(spec, no):
            rows.append((req, no, stage, "todo", "-", "-", ""))
    with OUT.open("w", encoding="utf-8", newline="\n") as f:
        f.write("req\tspec\tstage\tstatus\timpl\treceipt\tnote\n")
        for r in rows:
            f.write("\t".join(r) + "\n")
    print(f"{len(rows)} rows -> {OUT.name}")
    unknown = [r for r in rows if r[2] == "?"]
    if unknown:
        print("UNSTAGED:", unknown)

if __name__ == "__main__":
    main()
