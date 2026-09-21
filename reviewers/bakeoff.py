# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Model bake-off for the security gate: the same handoff, every candidate model, several
repetitions, scored against defects known to be in the range.

    python .engine/reviewers/bakeoff.py --handoff .engine/local/handoff-U-R.md --repeat 3 \
        --model gemma4:31b-it-q4_K_M --model llama3.1:8b-instruct-q8_0 \
        --truth "src/app.py|self.store.delete|delete route lacks the owner guard" \
        --truth "src/app.py|json.loads|malformed JSON body is an unhandled exception"

Each --truth is file|quote-fragment|label: a planted defect counts as found when a grounded
finding names that file and its quote or description contains the fragment. Nothing is
submitted to the gate log; the verdict files are copied aside per model and repetition,
and a table is printed and written as JSON. The scores are: valid verdict (the harness's
completeness rules met), verdict fail/pass, truths found, ungrounded findings (hallucination
count), inconsistent findings, seconds, tokens per second. A model that cannot produce a
valid verdict is not up to the task, however fluent its output.
"""
import argparse
import json
import pathlib
import re
import shutil
import subprocess
import sys
import time


def run_one(driver, handoff, model, num_ctx):
    t0 = time.time()
    res = subprocess.run([sys.executable, str(driver), "--model", model, "--num-ctx", str(num_ctx), str(handoff)],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    return time.time() - t0, res.returncode, res.stdout + res.stderr


def score(block, truths):
    """A truth is found when a grounded finding names its file and any one of its fragments (separated by
    `;`) appears in the quoted line or, case-insensitively, in the description. A reviewer that quotes a
    neighbouring line of the same defect and names it in prose has still found it."""
    grounded = block.get("findings_detail") or []
    found = []
    for file, frags, label in truths:
        hit = False
        for frag in [x.strip() for x in frags.split(";") if x.strip()]:
            hit = hit or any(f.get("file", "").endswith(file)
                             and (frag in str(f.get("quote", "")) or frag.lower() in str(f.get("description", "")).lower())
                             for f in grounded)
        found.append((label, hit))
    return found


def table(rows, models, truths):
    lines = ["| model | valid | truths found | ungrounded | inconsistent | mean s |", "|---|---|---|---|---|---|"]
    for model in models:
        mine = [r for r in rows if r["model"] == model]
        n = len(mine) or 1
        valid = sum(1 for r in mine if r["valid"])
        found = sum(sum(1 for v in r["found"].values() if v) for r in mine)
        lines.append(f"| {model} | {valid}/{len(mine)} | {found}/{len(mine) * len(truths)} | {sum(r['ungrounded'] for r in mine)} | "
                     f"{sum(r['inconsistent'] for r in mine)} | {sum(r['seconds'] for r in mine) / n:.0f} |")
    return "\n".join(lines)


def rescore(out, truths):
    """Re-score the saved verdict copies against a new truth list; nothing is re-run."""
    rp = out / "results.json"
    rows = json.loads(rp.read_text(encoding="utf-8"))
    for row in rows:
        slug = re.sub(r"[^A-Za-z0-9]+", "-", row["model"]).strip("-")
        vf = out / f"{slug}-rep{row['rep']}.json"
        if vf.is_file():
            row["found"] = {label: hit for label, hit in score(json.loads(vf.read_text(encoding="utf-8")), truths)}
    rp.write_text(json.dumps(rows, indent=1), encoding="utf-8", newline="\n")
    models = list(dict.fromkeys(r["model"] for r in rows))
    for r in rows:
        print(f"{r['model']} rep {r['rep']}: found={[k for k, v in r['found'].items() if v]}")
    print()
    print(table(rows, models, truths))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--handoff", required=True)
    ap.add_argument("--model", action="append", required=True)
    ap.add_argument("--truth", action="append", default=[], help="file|fragment[;fragment...]|label")
    ap.add_argument("--rescore", action="store_true", help="re-score the saved verdict copies against --truth; run nothing")
    ap.add_argument("--repeat", type=int, default=3)
    ap.add_argument("--num-ctx", type=int, default=16384)
    ap.add_argument("--out", default=".engine/local/bakeoff")
    a = ap.parse_args(argv)
    handoff = pathlib.Path(a.handoff).resolve()
    root = handoff.parent.parent.parent
    driver = pathlib.Path(__file__).resolve().parent / "local_model.py"
    truths = [tuple(t.split("|", 2)) for t in a.truth]
    m = re.match(r"^# GATE HANDOFF: (\S+) run (\d+)", handoff.read_text(encoding="utf-8"))
    unit, run = m.group(1), m.group(2)
    out = root / a.out
    out.mkdir(parents=True, exist_ok=True)
    if a.rescore:
        return rescore(out, truths)
    rows = []
    for model in a.model:
        slug = re.sub(r"[^A-Za-z0-9]+", "-", model).strip("-")
        for i in range(1, a.repeat + 1):
            secs, code, log = run_one(driver, handoff, model, a.num_ctx)
            vf = root / ".engine" / "local" / f"verdict-{unit}-{run}-{slug}.json"
            row = {"model": model, "rep": i, "seconds": round(secs, 1), "driver_exit": code, "valid": False, "verdict": "-",
                   "grounded": 0, "blocking": 0, "ungrounded": 0, "inconsistent": 0, "tok_s": None, "found": {}}
            if code == 0 and vf.is_file():
                b = json.loads(vf.read_text(encoding="utf-8"))
                shutil.copy(vf, out / f"{slug}-rep{i}.json")
                remaining = re.search(r"after repair, (\d+) completeness problem", log)
                first = re.search(r"would be refused \((\d+)\)", log)
                row.update(valid=(remaining and remaining.group(1) == "0") or (not first), verdict=b["verdict"],
                           grounded=b["open_findings"], blocking=b["blocking_findings"], ungrounded=len(b.get("ungrounded_findings", [])),
                           inconsistent=len(b.get("inconsistent_findings", [])),
                           tok_s=round(b["model_runtime"]["eval_count"] / max(b["model_runtime"]["total_duration_s"], 0.1), 1),
                           found={label: hit for label, hit in score(b, truths)})
            else:
                row["error"] = log.strip().splitlines()[-1][:160] if log.strip() else f"exit {code}"
            rows.append(row)
            (out / f"{slug}-rep{i}.log").write_text(log, encoding="utf-8", newline="\n")
            print(f"{model} rep {i}: {'valid' if row['valid'] else 'INVALID'} {row['verdict']} grounded={row['grounded']} blocking={row['blocking']} "
                  f"ungrounded={row['ungrounded']} inconsistent={row['inconsistent']} found={[k for k, v in row['found'].items() if v]} "
                  f"{row['seconds']}s {row['tok_s']} tok/s" + (f" ERROR {row['error']}" if row.get("error") else ""), flush=True)
    (out / "results.json").write_text(json.dumps(rows, indent=1), encoding="utf-8", newline="\n")
    print()
    print(table(rows, a.model, truths))
    print(f"\nresults: {out / 'results.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
