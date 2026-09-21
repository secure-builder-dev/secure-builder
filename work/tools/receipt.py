# © 2026 Casey Houle. All rights reserved.
"""receipt — performs a mutation and writes the receipt from captured output.

    python tools/receipt.py SPEC REQ CHECK FILE OLD NEW "description" -- test command...

The mutation is a property-level edit: OLD is replaced by NEW in FILE (OLD must
occur exactly once). The test command runs with the property broken, then the
file is restored byte-for-byte and verified, then the test runs again. The
receipt is written only if the broken run failed and the restored run passed.
Otherwise nothing is written and the exit code says why — a mutation that does
not break the check is a finding against the test (spec 05 REQ-3.4).

A mutation whose description reads as a removal is refused (spec 07 §2.2).
"""
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent   # work/tools -> the repository
BROKEN_HDR = "--- output with the property broken (must show failure) ---"
RESTORED_HDR = "--- output with the property restored (must show success) ---"


def clear_bytecode():
    """A same-size edit within one second is invisible to the bytecode cache and
    the stale .pyc would run instead of the mutated source. Clear it every time."""
    import shutil
    for d in list(ROOT.rglob("__pycache__")):
        shutil.rmtree(d, ignore_errors=True)


def run(cmd):
    import os
    clear_bytecode()
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    res = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True,
                         encoding="utf-8", errors="replace", env=env)
    home = str(pathlib.Path.home())
    out = [l.replace(home, "~").replace(home.replace("\\", "/"), "~")
           for l in (res.stdout + res.stderr).strip().splitlines()]
    keep = [l for l in out if re.search(r"\b(FAIL|ERROR|OK|Ran |passed|failed|AssertionError)", l)] or out[-6:]
    return res.returncode, keep[-8:]


def make(spec, req, check, file, old, new, description, test_cmd):
    if re.search(r"\b(delet|remov|renam|rm\b)", description, re.I):
        return f"refused: mutation description reads as a removal: {description!r}"
    path = ROOT / file
    original = path.read_bytes()
    text = original.decode("utf-8")
    if text.count(old) != 1:
        return f"refused: OLD occurs {text.count(old)} times in {file}, must be exactly once"
    try:
        path.write_bytes(text.replace(old, new).encode("utf-8"))
        rc_b, out_b = run(test_cmd)
    finally:
        path.write_bytes(original)
    if path.read_bytes() != original:
        return f"restore FAILED for {file} — investigate before doing anything else"
    rc_r, out_r = run(test_cmd)
    if rc_b == 0 or not any("FAIL" in l or "ERROR" in l for l in out_b):
        return (f"NOT WRITTEN: broken run exited {rc_b} — the mutation did not break the check. "
                f"Fix the test, not the code.\n  " + "\n  ".join(out_b))
    if rc_r != 0:
        return f"NOT WRITTEN: restored run exited {rc_r} — the suite is red before mutation.\n  " + "\n  ".join(out_r)
    shown = ["python" if c == sys.executable else c for c in test_cmd]
    receipt = ROOT / "records" / "receipts" / f"{spec}-{req}.txt"
    receipt.parent.mkdir(parents=True, exist_ok=True)
    body = (f"REQ:        {req}\nSPEC:       {spec}\nCHECK:      {check}\n"
            f"MUTATION:   {description}\nFILE:       {file}\nTEST:       {' '.join(shown)}\n"
            f"{BROKEN_HDR}\n" + "\n".join(out_b) + f"\nexit {rc_b}\n"
            f"{RESTORED_HDR}\n" + "\n".join(out_r) + f"\nexit {rc_r}\n")
    receipt.write_text(body, encoding="utf-8", newline="\n")
    return f"wrote {receipt.relative_to(ROOT).as_posix()}"


def main(argv):
    if "--" not in argv or len(argv) < 9:
        print(__doc__)
        return 2
    i = argv.index("--")
    spec, req, check, file, old, new, description = argv[:i]
    old = old.encode("utf-8").decode("unicode_escape")
    new = new.encode("utf-8").decode("unicode_escape")
    msg = make(spec, req, check, file, old, new, description, argv[i + 1:])
    print(msg)
    return 0 if msg.startswith("wrote") else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
