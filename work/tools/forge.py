# © 2026 Casey Houle. All rights reserved.
"""forge — run the engine's own fix queue through the local build models, unattended.

    python work/tools/forge.py [--queue work/tasks/queue.json] [--only ENG-03]

For each task not yet done: a test model writes a failing regression test
(build_model --phase tests), build models write the fix (--phase build, models
rotated), then the full self-test suite and `check` must be green. Green: the
task's files are committed and pushed. Anything else: the task's files are
restored, the outcome is logged, and the next task starts. State lives in
work/tasks/state.json; the log in work/tasks/forge.log. Nothing here writes code:
every line of the fix and its test comes from a local model.
"""
import argparse
import datetime
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
TASKS = ROOT / "work" / "tasks"
PY = sys.executable.replace("\\", "/")   # shlex in the driver would eat Windows backslashes
TEST_MODELS = "gemma4:31b-it-q4_K_M,devstral:24b-small-2505-q4_K_M"
BUILD_MODELS = "devstral:24b-small-2505-q4_K_M,gemma4:31b-it-q4_K_M,mistral-small3.2:24b-instruct-2506-q4_K_M"


def log(msg):
    line = f"{datetime.datetime.now().isoformat(timespec='seconds')} {msg}"
    print(line, flush=True)
    with open(TASKS / "forge.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")


def sh(cmd, cwd=ROOT, timeout=7200):
    r = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    return r.returncode, r.stdout + r.stderr


def load_state():
    p = TASKS / "state.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}


def save_state(state):
    (TASKS / "state.json").write_text(json.dumps(state, indent=1) + "\n", encoding="utf-8", newline="\n")


def revert(paths):
    for p in paths:
        code, _ = sh(["git", "ls-files", "--error-unmatch", p])
        if code == 0:
            sh(["git", "checkout", "--", p])
        else:
            (ROOT / p).unlink(missing_ok=True)


def driver(task, phase, models, rounds, test_cmd, extra_tests=None):
    args = [PY, "-u", "harness/reviewers/build_model.py", "--root", ".", "--task", f"work/tasks/{task['id']}.md",
            "--phase", phase, "--model", models, "--rounds", str(rounds), "--num-ctx", "32768",
            "--source", task["source"], "--tests", extra_tests or task["test_file"],
            "--test-cmd", test_cmd, "--test-cwd", "harness"]
    for c in task.get("context", []):
        args += ["--context", c]
    code, out = sh(args)
    (TASKS / f"{task['id']}-{phase}.log").write_text(out, encoding="utf-8", newline="\n")
    used = re.findall(r"round \d+ with (\S+);", out)
    return code, out, (used[-1] if used else "")


def run_task(task, state):
    tid = task["id"]
    task["test_file"] = f"harness/selftest/test_{tid.lower().replace('-', '')}_{task['slug']}.py"
    module = "selftest." + pathlib.Path(task["test_file"]).stem
    sources = [s for s in task["source"].split(",") if s]
    touched = sources + [task["test_file"]]
    (TASKS / f"{tid}.md").write_text(f"# {tid}\n\n{task['spec']}\n", encoding="utf-8", newline="\n")
    log(f"{tid}: tests phase ({TEST_MODELS})")
    code, out, tmodel = driver(task, "tests", TEST_MODELS, 6, f"{PY} -m unittest {module}")
    if code != 0:
        revert(touched)
        state[tid] = {"status": "failed: no failing test written", "at": datetime.datetime.now().isoformat(timespec="seconds")}
        log(f"{tid}: FAILED in the tests phase\n{out[-1500:]}")
        return
    log(f"{tid}: failing test written by {tmodel}; build phase ({BUILD_MODELS})")
    code, out, bmodel = driver(task, "build", BUILD_MODELS, 9, f"{PY} -m unittest {module}")
    if code != 0:
        revert(touched)
        state[tid] = {"status": "failed: not converged", "test_model": tmodel, "at": datetime.datetime.now().isoformat(timespec="seconds")}
        log(f"{tid}: FAILED — build not converged\n{out[-1500:]}")
        return
    log(f"{tid}: task test green with {bmodel}; full self-test suite")
    code, out = sh([PY, "-m", "unittest", "discover", "-s", "selftest", "-t", "."], cwd=ROOT / "harness")
    if code != 0:
        log(f"{tid}: regression in the full suite; one repair build against the whole suite\n{out[-1200:]}")
        code, out, bmodel = driver(task, "build", BUILD_MODELS, 4, f"{PY} -m unittest discover -s selftest -t .",
                                   extra_tests=task["test_file"])
        if code != 0:
            revert(touched)
            state[tid] = {"status": "failed: regression in the full suite", "at": datetime.datetime.now().isoformat(timespec="seconds")}
            log(f"{tid}: FAILED — regression not repaired\n{out[-1500:]}")
            return
    code, out = sh([PY, "harness/run.py", "check"])
    if code != 0:
        revert(touched)
        state[tid] = {"status": "failed: check red", "at": datetime.datetime.now().isoformat(timespec="seconds")}
        log(f"{tid}: FAILED — check red\n{out[-1500:]}")
        return
    sh(["git", "add", "--", *touched, f"work/tasks/{tid}.md"])
    msg = f"{tid} {task['slug']}: test by {tmodel}, fix by {bmodel} (local models, forge)"
    code, out = sh(["git", "commit", "-q", "-m", msg])
    if code != 0:
        log(f"{tid}: commit refused\n{out[-800:]}")
        state[tid] = {"status": "failed: commit refused", "at": datetime.datetime.now().isoformat(timespec="seconds")}
        return
    pcode, pout = sh(["git", "push", "-q", "origin", "HEAD"])
    state[tid] = {"status": "done", "test_model": tmodel, "build_model": bmodel, "pushed": pcode == 0,
                  "commit": sh(["git", "rev-parse", "--short", "HEAD"])[1].strip(), "at": datetime.datetime.now().isoformat(timespec="seconds")}
    log(f"{tid}: DONE {state[tid]['commit']} ({msg}); push {'ok' if pcode == 0 else 'FAILED: ' + pout[-300:]}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue", default="work/tasks/queue.json")
    ap.add_argument("--only")
    a = ap.parse_args(argv)
    queue = json.loads((ROOT / a.queue).read_text(encoding="utf-8"))
    state = load_state()
    for task in queue:
        if a.only and task["id"] != a.only:
            continue
        if state.get(task["id"], {}).get("status") == "done":
            continue
        try:
            run_task(task, state)
        except Exception as e:      # noqa: BLE001 - an unattended loop logs and moves on
            log(f"{task['id']}: ERROR {type(e).__name__}: {e}")
            state[task["id"]] = {"status": f"error: {e}"}
        save_state(state)
    done = sum(1 for v in state.values() if v.get("status") == "done")
    log(f"forge: queue finished — {done} done, {len(state) - done} not done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
