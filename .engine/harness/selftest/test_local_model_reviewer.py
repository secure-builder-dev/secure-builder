# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""The local-model reviewer end to end against a faked loopback runtime: refusals, grounding, the thinking retry."""
import contextlib
import importlib.util
import io
import json
import pathlib
import unittest
from unittest import mock

from selftest.helpers import commit, git, git_repo, tree, write

ROOT = pathlib.Path(__file__).resolve().parent.parent
REVIEWERS = ROOT / "reviewers" if (ROOT / "reviewers").is_dir() else ROOT.parent / "reviewers"


def load(name):
    spec = importlib.util.spec_from_file_location(name, REVIEWERS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


CHECKLIST = """- [base] B1. Input validation — every input is checked.
- [base] B2. Authorization enforcement — role and scope rules.
- [base:informational] I1. Logging hygiene.
"""

SERVER = """import json


def handle(request):
    data = json.loads(request.body)
    return run_query("SELECT * FROM notes WHERE id = " + data["id"])
"""

GOOD = {q: ("- GET /notes (covered)\n- POST /notes (covered)" if q in ("Q3", "Q4")
            else "I examined handle() and every path through run_query.") for q in ("Q1", "Q2", "Q3", "Q4", "Q5", "Q6")}


def judgment(**over):
    j = {"verdict": "pass", "manifest_result": "declared and implemented", "platform_surface": "none",
         "findings": [], "checklist": [{"item": "B1", "result": "pass", "evidence": "ok"},
                                       {"item": "B2", "result": "pass", "evidence": "ok"}],
         "completeness": {"SC-1": dict(GOOD)}, "summary": "fine"}
    j.update(over)
    return j


def chat(content, done_reason="stop", thinking="", **extra):
    out = {"message": {"role": "assistant", "content": content, **({"thinking": thinking} if thinking else {})},
           "done_reason": done_reason, "eval_count": 42, "prompt_eval_count": 7, "total_duration": 3_000_000_000,
           "context": [1, 2, 3]}
    out.update(extra)
    return out


class Runtime:
    """A loopback Ollama stand-in: /api/show and /api/tags answer the identity, /api/chat pops replies in order."""

    def __init__(self, *replies, show_error=None):
        self.replies = list(replies)
        self.chats = []
        self.show_error = show_error

    def __call__(self, req, timeout=None):
        url = req if isinstance(req, str) else req.full_url
        if url.endswith("/api/show"):
            if self.show_error:
                raise self.show_error
            return Resp(json.dumps({"details": {"family": "gemma", "parameter_size": "31B", "quantization_level": "Q4"}}).encode())
        if url.endswith("/api/tags"):
            return Resp(json.dumps({"models": [{"name": "other", "digest": "ffff"},
                                               {"name": "m:1", "digest": "abcdef0123456789"}]}).encode())
        if url.endswith("/api/chat"):
            self.chats.append(json.loads(req.data.decode("utf-8")))
            reply = self.replies.pop(0)
            if isinstance(reply, BaseException):
                raise reply
            return Resp(json.dumps(reply).encode("utf-8"))
        raise AssertionError(f"unexpected url {url}")


def project(root, manifest=None, quality=True, state=True, handoff=None, register=True):
    """A project with one committed change and a prepared gate run; returns the handoff path."""
    git_repo(root)
    write(root, "AGENTS.md", "# Agents\n\n## Project rules\n\n1. Validate input.\n\n## Other\n\nignored\n")
    write(root, "src/server.py", "# empty\n")
    base = commit(root, "base")
    write(root, "src/server.py", SERVER)
    write(root, ".engine/rules/control-manifest.json", manifest if manifest is not None else json.dumps(
        {"controls": [{"id": "SC-1", "description": "validation", "location": "src/server.py", "status": "implemented"},
                      {"id": "PH", "placeholder": True}]}))
    if register:
        write(root, ".engine/records/findings-register.md", "| id | x |\n|---|---|\n| F-1 | an old finding |\n")
    head = commit(root, "change")
    write(root, ".engine/rules/agents/security-gate.md", "You are the security gate.\n")
    write(root, ".engine/work/gate-U1-2-checklist.md", CHECKLIST)
    if state:
        write(root, ".engine/work/gate-U1-2.json", json.dumps(
            {"quality_passed": quality, "control_shaped": True, "checklist_version": "c1", "harness_version": "h1"}))
    text = handoff if handoff is not None else (
        f"# GATE HANDOFF: U1 run 2\nrange: {base}..{head}\nscan: CLEAN (0 findings)\nread first: a.md, b.md\n")
    return write(root, ".engine/work/handoff-U1-2.md", text)


def run(lm, runtime, *argv):
    out = io.StringIO()
    with mock.patch.object(lm.urllib.request, "urlopen", runtime), contextlib.redirect_stdout(out):
        code = lm.main(list(argv))
    return code, out.getvalue().splitlines()


def verdict(root):
    return json.loads((root / ".engine/work/verdict-U1-2-m-1.json").read_text(encoding="utf-8"))


class Main(unittest.TestCase):
    def test_a_clean_review_writes_a_pass_verdict_from_the_record(self):
        lm = load("local_model")
        with tree() as root:
            hp = project(root)
            rt = Runtime(chat(json.dumps(judgment())))
            code, lines = run(lm, rt, "--model", "m:1", str(hp))
            self.assertEqual(code, 0, lines)
            v = verdict(root)
        self.assertEqual(v["verdict"], "pass")
        self.assertEqual(v["tier"], "security")
        self.assertEqual(v["run"], "2")
        self.assertEqual(v["control_shaped"], "yes")
        self.assertEqual(v["scan_verdict"], "CLEAN (0 findings)")
        self.assertEqual(v["model"], "m:1 (gemma; 31B; Q4; ollama digest abcdef012345)")
        self.assertEqual(v["completeness_blocks"], "no")
        self.assertEqual(v["model_runtime"], {"think": "model default", "thinking_chars": 0, "total_duration_s": 3.0,
                                              "eval_count": 42, "prompt_eval_count": 7})
        self.assertEqual(len(rt.chats), 1)
        self.assertNotIn("think", rt.chats[0])
        prompt = rt.chats[0]["messages"][1]["content"]
        self.assertIn("run_query", prompt)
        self.assertIn("1. Validate input.", prompt)
        self.assertNotIn("ignored", prompt, "only the Project rules section is quoted")
        self.assertIn("F-1 | an old finding", prompt)
        self.assertNotIn('"id": "PH"', prompt.split("Checklist prepared")[0], "placeholder controls are not reviewed")
        self.assertTrue(any(l.startswith("local_model: PASS — 0 grounded finding(s)") for l in lines), lines)
        self.assertTrue(any("verdict block written to .engine/work/verdict-U1-2-m-1.json" in l for l in lines), lines)

    def test_findings_are_sorted_into_grounded_ungrounded_inconsistent_and_informational(self):
        lm = load("local_model")
        quote = 'return run_query("SELECT * FROM notes WHERE id = " + data["id"])'
        findings = [
            {"id": "F1", "severity": "blocking", "checklist_item": "B1. Input validation", "file": "src/server.py",
             "quote": "+    " + quote, "description": "SQL injection", "fix": "parameterize"},
            {"id": "F2", "severity": "non-blocking", "checklist_item": "B1", "file": "src/server.py",
             "quote": "os.system(cmd)", "description": "invented", "fix": "x"},
            {"id": "F3", "severity": "non-blocking", "checklist_item": "B1", "file": "src/server.py",
             "quote": "@@ -1 +1,6 @@", "description": "in the diff but proves nothing", "fix": "x"},
            {"id": "F4", "severity": "blocking", "checklist_item": "B2. Authorization", "file": "src/server.py",
             "quote": "data = json.loads(request.body)", "description": "judged pass elsewhere", "fix": "x"},
            {"id": "F5", "severity": "non-blocking", "checklist_item": "I1. Logging", "file": "src/server.py",
             "quote": "def handle(request):", "description": "note only", "fix": "x"},
        ]
        j = judgment(verdict="pass", findings=findings,
                     checklist=[{"item": "B1. Input validation", "result": "finding", "evidence": "injection"},
                                {"item": "B2", "result": "pass", "evidence": "ok"}])
        with tree() as root:
            hp = project(root)
            code, lines = run(lm, Runtime(chat(json.dumps(j))), "--model", "m:1", "--reviewer-class",
                              "automated-with-human-review", str(hp))
            self.assertEqual(code, 0, lines)
            v = verdict(root)
        self.assertEqual(v["verdict"], "fail", "a grounded blocking finding overrides the model's pass")
        self.assertEqual(v["finding_ids"], ["F1"])
        self.assertEqual(v["findings_detail"][0]["line"], 6, "line number from version control")
        self.assertEqual(v["blocking_findings"], 1)
        self.assertEqual([f["id"] for f in v["ungrounded_findings"]], ["F2", "F3"])
        self.assertEqual([f["id"] for f in v["inconsistent_findings"]], ["F4"])
        self.assertEqual([f["id"] for f in v["informational_notes"]], ["F5"])
        self.assertEqual(v["reviewer_class"], "automated-with-human-review")
        self.assertTrue(any(l.startswith("local_model: FAIL — 1 grounded finding(s), 1 blocking; 2 ungrounded") for l in lines), lines)
        self.assertIn("  - [blocking] F1 B1. Input validation src/server.py:6 — SQL injection", lines)
        self.assertTrue(any(l.startswith("  - [inconsistent] F4") for l in lines), lines)
        self.assertTrue(any(l.startswith("  - [ungrounded] F2") for l in lines), lines)

    def test_a_bare_completeness_answer_marks_completeness_blocks(self):
        lm = load("local_model")
        bare = dict(GOOD, Q1="pass")
        with tree() as root:
            hp = project(root)
            # the first answer is bare; every repair pass fails to answer, so the bare set is kept
            rt = Runtime(chat(json.dumps(judgment(completeness={"SC-1": bare}))),
                         lm.urllib.error.URLError("down"), chat("not json"), chat(json.dumps({"SC-1": bare})))
            code, lines = run(lm, rt, "--model", "m:1", str(hp))
            self.assertEqual(code, 0, lines)
            v = verdict(root)
        self.assertEqual(len(rt.chats), 4)
        self.assertEqual(v["completeness_blocks"], "yes")
        self.assertTrue(any("repair pass 3 of 3" in l for l in lines), lines)


class ThinkingRetry(unittest.TestCase):
    def test_a_reply_that_thought_out_its_budget_is_retried_once_with_thinking_off(self):
        lm = load("local_model")
        with tree() as root:
            hp = project(root)
            rt = Runtime(chat("", done_reason="length", thinking="hmm " * 50),
                         chat(json.dumps(judgment())))
            code, lines = run(lm, rt, "--model", "m:1", str(hp))
            self.assertEqual(code, 0, lines)
            v = verdict(root)
            raw = json.loads((root / ".engine/work/raw-U1-2-m-1.json").read_text(encoding="utf-8"))
        self.assertEqual(len(rt.chats), 2, "exactly one retry")
        self.assertNotIn("think", rt.chats[0])
        self.assertIs(rt.chats[1]["think"], False)
        self.assertEqual(v["model_runtime"]["think"], "off (retried: thinking used the whole answer budget)")
        self.assertEqual(raw["done_reason"], "length")
        self.assertNotIn("context", raw, "the raw answer is kept without the context vector")
        self.assertTrue(any("retrying once with thinking off" in l for l in lines), lines)

    def test_a_reply_that_fails_for_another_reason_is_not_retried(self):
        lm = load("local_model")
        with tree() as root:
            hp = project(root)
            rt = Runtime(chat("this is not json", done_reason="stop"), chat(json.dumps(judgment())))
            code, lines = run(lm, rt, "--model", "m:1", str(hp))
            self.assertFalse((root / ".engine/work/verdict-U1-2-m-1.json").exists())
            self.assertTrue((root / ".engine/work/raw-U1-2-m-1.json").is_file())
        self.assertEqual(code, 2)
        self.assertEqual(len(rt.chats), 1)
        self.assertTrue(any(l.startswith("local_model: COULD NOT RUN — the model did not return a verdict") and
                            "done_reason='stop'" in l and "raw answer kept at raw-U1-2-m-1.json" in l for l in lines), lines)

    def test_no_think_is_never_retried(self):
        lm = load("local_model")
        with tree() as root:
            hp = project(root)
            rt = Runtime(chat("", done_reason="length", thinking="hmm"), chat(json.dumps(judgment())))
            code, lines = run(lm, rt, "--model", "m:1", "--no-think", str(hp))
        self.assertEqual(code, 2)
        self.assertEqual(len(rt.chats), 1)
        self.assertIs(rt.chats[0]["think"], False)
        self.assertTrue(any(l.startswith("local_model: COULD NOT RUN — the model did not return a verdict") for l in lines), lines)

    def test_no_think_is_recorded_in_a_successful_verdict(self):
        lm = load("local_model")
        with tree() as root:
            hp = project(root)
            code, lines = run(lm, Runtime(chat(json.dumps(judgment()), thinking="ab")), "--model", "m:1", "--no-think", str(hp))
            self.assertEqual(code, 0, lines)
            v = verdict(root)
        self.assertEqual(v["model_runtime"]["think"], "off")
        self.assertEqual(v["model_runtime"]["thinking_chars"], 2)

    def test_thought_out_needs_length_empty_content_and_thinking(self):
        lm = load("local_model")
        for reply, expect in [(chat("", "length", "t"), True), (chat("  ", "length", "t"), True),
                              (chat("", "stop", "t"), False), (chat("", "length"), False), (chat("{", "length", "t"), False)]:
            with mock.patch.object(lm.urllib.request, "urlopen", Runtime(reply)):
                with self.assertRaises(lm.NoVerdict) as e:
                    lm.ask("http://127.0.0.1:1", "m", "s", "u", 1024)
            self.assertIs(e.exception.thought_out, expect, reply)
            self.assertNotIn("raw answer kept", str(e.exception))

    def test_a_reply_with_no_message_is_no_verdict(self):
        lm = load("local_model")
        with mock.patch.object(lm.urllib.request, "urlopen", Runtime({"done_reason": "stop"})):
            with self.assertRaises(lm.NoVerdict) as e:
                lm.ask("http://127.0.0.1:1", "m", "s", "u", 1024)
        self.assertIn("content=0 chars", str(e.exception))


class Refusals(unittest.TestCase):
    def test_an_endpoint_off_the_loopback_interface_is_refused(self):
        lm = load("local_model")
        rt = Runtime()
        code, lines = run(lm, rt, "--model", "m:1", "--endpoint", "http://10.0.0.5:11434", "h.md")
        self.assertEqual(code, 2)
        self.assertEqual(lines, ["local_model: REFUSED — endpoint http://10.0.0.5:11434 is not the loopback interface; "
                                 "a local reviewer never leaves the box"])
        self.assertEqual(rt.chats, [])

    def test_a_missing_model_argument_is_a_usage_error(self):
        lm = load("local_model")
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as e:
            lm.main(["h.md"])
        self.assertEqual(e.exception.code, 2)

    def test_a_handoff_without_a_range_cannot_run(self):
        lm = load("local_model")
        with tree() as root:
            hp = project(root, handoff="# GATE HANDOFF: U1 run 2\n")
            code, lines = run(lm, Runtime(), "--model", "m:1", str(hp))
        self.assertEqual((code, lines), (2, ["local_model: COULD NOT RUN — handoff lacks base"]))

    def test_an_unprepared_run_cannot_run(self):
        lm = load("local_model")
        with tree() as root:
            hp = project(root, state=False)
            code, lines = run(lm, Runtime(), "--model", "m:1", str(hp))
        self.assertEqual(code, 2)
        self.assertEqual(lines, ["local_model: COULD NOT RUN — no prepared run at gate-U1-2.json; run `gate prepare` first"])

    def test_a_run_that_failed_the_quality_gate_stops(self):
        lm = load("local_model")
        with tree() as root:
            hp = project(root, quality=False)
            code, lines = run(lm, Runtime(), "--model", "m:1", str(hp))
        self.assertEqual(code, 1)
        self.assertTrue(lines[0].startswith("local_model: STOP — the handoff's run did not pass the quality gate"))

    def test_a_model_the_runtime_does_not_hold_is_named(self):
        lm = load("local_model")
        with tree() as root:
            hp = project(root)
            err = lm.urllib.error.HTTPError("http://127.0.0.1:11434/api/show", 404, "nf", {}, None)
            code, lines = run(lm, Runtime(show_error=err), "--model", "m:1", str(hp))
        self.assertEqual(code, 2)
        self.assertTrue(lines[0].startswith("local_model: COULD NOT RUN — the runtime does not hold model 'm:1' (HTTP 404)"), lines)

    def test_an_unreachable_runtime_is_named(self):
        lm = load("local_model")
        with tree() as root:
            hp = project(root)
            code, lines = run(lm, Runtime(show_error=lm.urllib.error.URLError("refused")), "--model", "m:1", str(hp))
        self.assertEqual(code, 2)
        self.assertTrue(lines[0].startswith("local_model: COULD NOT RUN — model runtime not reachable on the loopback interface"), lines)

    def test_a_review_larger_than_the_context_is_refused_not_truncated(self):
        lm = load("local_model")
        with tree() as root:
            hp = project(root)
            rt = Runtime()
            code, lines = run(lm, rt, "--model", "m:1", "--num-ctx", "100", str(hp))
        self.assertEqual(code, 2)
        self.assertEqual(rt.chats, [])
        self.assertTrue(lines[0].startswith("local_model: COULD NOT RUN — the review needs about "), lines)
        self.assertIn("is given 100", lines[0])

    def test_an_unreadable_manifest_means_no_controls(self):
        lm = load("local_model")
        with tree() as root:
            hp = project(root, manifest="{not json", register=False)
            rt = Runtime(chat(json.dumps(judgment(completeness={}))))
            code, lines = run(lm, rt, "--model", "m:1", str(hp))
            self.assertEqual(code, 0, lines)
            v = verdict(root)
        self.assertEqual(len(rt.chats), 1, "no controls, nothing to repair")
        self.assertEqual(v["completeness"], {})
        self.assertNotIn("Findings register", rt.chats[0]["messages"][1]["content"])


class Helpers(unittest.TestCase):
    def test_handoff_facts_reads_unit_range_scan_and_read_first(self):
        lm = load("local_model")
        facts = lm.handoff_facts("# GATE HANDOFF: U7 run 3\nrange: abc123..def456\nscan: CLEAN\nread first: a.md, b.md\nother\n")
        self.assertEqual(facts, {"unit": "U7", "run": "3", "base": "abc123", "head": "def456", "scan": "CLEAN",
                                 "read_first": ["a.md", "b.md"]})

    def test_read_of_a_missing_file_is_empty(self):
        lm = load("local_model")
        with tree() as root:
            self.assertEqual(lm.read(root / "nope.txt"), "")
            write(root, "x.txt", "hi")
            self.assertEqual(lm.read(root / "x.txt"), "hi")

    def test_completeness_problems_names_missing_bare_and_unlisted_answers(self):
        lm = load("local_model")
        controls = [{"id": "A"}, {"id": "B"}, {"id": "C"}]
        answers = {"A": "not a dict",
                   "B": dict(GOOD, Q2="n/a", Q5=""),
                   "C": dict(GOOD, Q3="Every route was reviewed carefully and found covered.")}
        probs = lm.completeness_problems(answers, controls)
        self.assertEqual(probs[0], "A: no answers")
        self.assertIn("B Q2: bare or empty answer; write what you examined", probs)
        self.assertIn("B Q5: bare or empty answer; write what you examined", probs)
        self.assertTrue(any(p.startswith("C Q3: must be a list") for p in probs), probs)
        self.assertEqual(len(probs), 4)
        self.assertEqual(lm.completeness_problems({"A": GOOD}, [{"id": "A"}]), [])

    def test_is_enumeration_accepts_lists_and_single_routes(self):
        lm = load("local_model")
        for a in ["- GET /notes", "a, b", "1. first", "DELETE /notes/<id>", "token expiry", "store.delete"]:
            self.assertTrue(lm.is_enumeration(a), a)
        for a in ["Everything was covered.", "the handler checks the token here"]:
            self.assertFalse(lm.is_enumeration(a), a)

    def test_repair_returns_complete_answers_untouched_without_asking(self):
        lm = load("local_model")
        rt = Runtime()
        with mock.patch.object(lm.urllib.request, "urlopen", rt):
            out = lm.repair_completeness("http://127.0.0.1:1", "m", "s", "u", {"A": GOOD}, [{"id": "A"}], 1024)
        self.assertEqual(out, {"A": GOOD})
        self.assertEqual(rt.chats, [])

    def test_repair_raises_temperature_on_later_passes_and_stops_when_clean(self):
        lm = load("local_model")
        bare = dict(GOOD, Q1="ok", Q2="ok")
        better = dict(GOOD, Q1="ok")
        rt = Runtime(chat(json.dumps({"A": bare})), chat(json.dumps({"A": better})), chat(json.dumps({"A": GOOD})))
        with mock.patch.object(lm.urllib.request, "urlopen", rt), contextlib.redirect_stdout(io.StringIO()) as out:
            got = lm.repair_completeness("http://127.0.0.1:1", "m", "s", "u", {"A": bare}, [{"id": "A"}], 1024)
        self.assertEqual(got, {"A": GOOD})
        self.assertEqual([c["options"]["temperature"] for c in rt.chats], [0.0, 0.2, 0.4])
        self.assertIn("after repair pass 3, 0 completeness problem(s) remain", out.getvalue())

    def test_item_of_and_substantive(self):
        lm = load("local_model")
        ids = {"B1", "I1"}
        self.assertEqual(lm.item_of({"checklist_item": "B1. Input", "id": "F1"}, ids, "checklist_item", "id"), "B1")
        self.assertEqual(lm.item_of({"checklist_item": "prose", "id": "I1"}, ids, "checklist_item", "id"), "I1")
        self.assertEqual(lm.item_of({"id": "F1"}, ids, "checklist_item", "id"), "")
        self.assertTrue(lm.substantive("data = json.loads(body)"))
        self.assertFalse(lm.substantive("return x"))
        self.assertFalse(lm.substantive("(((((((((("))

    def test_vendored_paths_and_malformed_numstat(self):
        lm = load("local_model")
        self.assertTrue(lm.vendored("web/node_modules/x/y.js"))
        self.assertFalse(lm.vendored("vendor.js"))
        shown, held = lm.held_back_files("garbage line\n3000\t0\tdata.csv\n2\t0\tthird_party/lib.py\n1\t1\tsrc/a.py\n")
        self.assertEqual(shown, ["src/a.py"])
        self.assertEqual(held, ["./: 1 bulk data file(s), not shown (data.csv)",
                                "third_party/: 1 vendored third-party file(s), not shown (third_party/lib.py)"])

    def test_section_reads_one_heading_or_says_none(self):
        lm = load("local_model")
        text = "## A\none\n## B\ntwo\nthree\n## C\n"
        self.assertEqual(lm._section(text, "## B"), "two\nthree")
        self.assertEqual(lm._section(text, "## Z"), "(none)")

    def test_line_of_reads_the_head_and_handles_no_file(self):
        lm = load("local_model")
        with tree() as root:
            git_repo(root)
            write(root, "a.py", "x = 1\n  y   =   2\n")
            head = commit(root)
            self.assertEqual(lm._line_of(root, head, "a.py", "y = 2"), 2)
            self.assertIsNone(lm._line_of(root, head, "a.py", "z = 3"))
            self.assertIsNone(lm._line_of(root, head, "", "x = 1"))

    def test_a_very_large_diff_is_truncated_and_says_so(self):
        lm = load("local_model")
        with tree() as root:
            git_repo(root)
            write(root, "README", "x\n")
            base = commit(root)
            for i in range(4):
                write(root, f"src/f{i}.py", "".join(f"value_{i}_{n} = {'z' * 60}\n" for n in range(450)))
            head = commit(root)
            self.assertEqual(git(root, "diff", "--numstat", f"{base}..{head}").returncode, 0)
            prompt = lm.build_prompt(root, {"unit": "U1", "run": "1", "base": base, "head": head}, "c", "d", [])
        self.assertIn("[diff truncated by the reviewer driver at 120000 characters; say so in the summary]", prompt)
        self.assertIn("Scan line from the handoff: not stated", prompt)


if __name__ == "__main__":
    unittest.main()
