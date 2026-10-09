# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""The reviewer repairs incomplete completeness answers in more than one pass and keeps the best set
(antipode ANTI-2 run 4: one pass left a bare answer and the grounded FAIL could not be recorded)."""
import importlib.util
import io
import json
import pathlib
import unittest
from unittest import mock

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


class Repair(unittest.TestCase):
    def test_a_second_pass_is_taken_and_the_complete_answers_are_kept(self):
        lm = load("local_model")
        controls = [{"id": "SC-18"}]
        good = {q: "- GET / (covered)\n- GET /api/antipode (covered)" if q in lm.ENUMERATE
                else "I examined end_headers and every response path through it." for q in lm.QUESTIONS}
        bare = dict(good, **{lm.QUESTIONS[-1]: "n/a"})
        replies = [{"SC-18": bare}, {"SC-18": good}]
        calls = []

        def fake(req, timeout=None):
            calls.append(1)
            return Resp(json.dumps({"message": {"content": json.dumps(replies[len(calls) - 1])}}).encode("utf-8"))
        self.assertTrue(lm.completeness_problems({"SC-18": bare}, controls))
        with mock.patch.object(lm.urllib.request, "urlopen", fake), mock.patch("builtins.print"):
            out = lm.repair_completeness("http://127.0.0.1:1", "m", "s", "u", {"SC-18": bare}, controls, 1024)
        self.assertEqual(len(calls), 2)
        self.assertEqual(lm.completeness_problems(out, controls), [])


if __name__ == "__main__":
    unittest.main()
