# © 2026 Casey Houle. All rights reserved.
"""ledger — mechanical row updates. Never regenerates; only amends one row at a time.

    python tools/ledger.py set SPEC REQ STATUS [impl=...] [receipt=...] [note=...]
    python tools/ledger.py show SPEC REQ
    python tools/ledger.py counts
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
LEDGER = ROOT / "ledger.tsv"
COLUMNS = ["req", "spec", "stage", "status", "impl", "receipt", "note"]


def read():
    lines = LEDGER.read_text(encoding="utf-8").splitlines()
    assert lines[0].split("\t") == COLUMNS, "ledger header drifted"
    return [dict(zip(COLUMNS, l.split("\t"))) for l in lines[1:] if l.strip()]


def write(rows):
    with LEDGER.open("w", encoding="utf-8", newline="\n") as f:
        f.write("\t".join(COLUMNS) + "\n")
        for r in rows:
            f.write("\t".join(r[c] for c in COLUMNS) + "\n")


def set_row(spec, req, status, **fields):
    rows = read()
    hit = [r for r in rows if r["spec"] == spec and r["req"] == req]
    if len(hit) != 1:
        raise SystemExit(f"ledger: {spec}/{req} matches {len(hit)} rows")
    r = hit[0]
    if status == "done":
        if not fields.get("impl") or not fields.get("receipt"):
            raise SystemExit("ledger: done requires impl= and receipt=")
        if not (ROOT / fields["receipt"]).is_file():
            raise SystemExit(f"ledger: receipt {fields['receipt']} does not exist; write it first")
    if status == "na" and not fields.get("note"):
        raise SystemExit("ledger: na requires note=")
    if status == "defer" and "v1." not in fields.get("note", ""):
        raise SystemExit("ledger: defer requires note= with a v1.x tag")
    r["status"] = status
    for k, v in fields.items():
        r[k] = v
    write(rows)
    return r


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    if argv[0] == "counts":
        rows = read()
        for st in ("todo", "doing", "done", "defer", "na"):
            print(f"{st}\t{sum(1 for r in rows if r['status'] == st)}")
        return 0
    if argv[0] == "show":
        for r in read():
            if r["spec"] == argv[1] and r["req"] == argv[2]:
                print(r)
        return 0
    if argv[0] == "set":
        spec, req, status = argv[1:4]
        fields = dict(a.split("=", 1) for a in argv[4:])
        r = set_row(spec, req, status, **fields)
        print(f"{spec}/{req} -> {status} {r['impl']} {r['receipt']}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
