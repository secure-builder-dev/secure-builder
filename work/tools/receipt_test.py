# © 2026 Casey Houle. All rights reserved.
"""Fixtures for tools/receipt.py — the build's mutation-as-acceptance mechanism
(spec 05 §3, spec 07 §2.2). Run: python tools/receipt_test.py"""
import pathlib
import shutil
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import receipt  # noqa: E402

IMPL = "THRESHOLD = 7\n"
TEST_OK = ("import sys, pathlib\n"
           "src = pathlib.Path(sys.argv[1]).read_text()\n"
           "ok = src.strip() == 'THRESHOLD = 7'\n"
           "print('OK' if ok else 'FAIL: threshold changed')\n"
           "sys.exit(0 if ok else 1)\n")
TEST_VACUOUS = "import sys\nprint('OK')\nsys.exit(0)\n"


class ReceiptTool(unittest.TestCase):
    def setUp(self):
        self.orig_root = receipt.ROOT
        self.root = pathlib.Path(tempfile.mkdtemp(prefix="receipt-fx-"))
        receipt.ROOT = self.root
        (self.root / "impl.py").write_text(IMPL, encoding="utf-8")
        (self.root / "t.py").write_text(TEST_OK, encoding="utf-8")

    def tearDown(self):
        receipt.ROOT = self.orig_root
        shutil.rmtree(self.root, ignore_errors=True)

    def cmd(self):
        return [sys.executable, "t.py", "impl.py"]

    def test_writes_receipt_when_mutation_breaks_check(self):
        msg = receipt.make("99", "REQ-1.1", "impl.py", "impl.py", "THRESHOLD = 7", "THRESHOLD = 700",
                           "raised the threshold", self.cmd())
        self.assertTrue(msg.startswith("wrote records/receipts"), msg)
        text = (self.root / "receipts/99-REQ-1.1.txt").read_text(encoding="utf-8")
        self.assertIn("FAIL: threshold changed", text.split("--- output with the property broken")[1].split("--- output with the property restored")[0])
        self.assertIn("exit 0", text.split("--- output with the property restored")[1])
        self.assertEqual((self.root / "impl.py").read_text(encoding="utf-8"), IMPL, "implementation must be restored")

    def test_refuses_when_mutation_does_not_break_check(self):
        (self.root / "t.py").write_text(TEST_VACUOUS, encoding="utf-8")
        msg = receipt.make("99", "REQ-1.2", "impl.py", "impl.py", "THRESHOLD = 7", "THRESHOLD = 700",
                           "raised the threshold", self.cmd())
        self.assertTrue(msg.startswith("NOT WRITTEN: broken run exited 0"), msg)
        self.assertFalse((self.root / "receipts/99-REQ-1.2.txt").exists())

    def test_refuses_removal_mutation(self):
        msg = receipt.make("99", "REQ-1.3", "impl.py", "impl.py", "THRESHOLD = 7", "",
                           "deleted the threshold line", self.cmd())
        self.assertTrue(msg.startswith("refused: mutation description reads as a removal"), msg)

    def test_refuses_ambiguous_old_string(self):
        (self.root / "impl.py").write_text("THRESHOLD = 7\nTHRESHOLD = 7\n", encoding="utf-8")
        msg = receipt.make("99", "REQ-1.4", "impl.py", "impl.py", "THRESHOLD = 7", "THRESHOLD = 8", "x", self.cmd())
        self.assertTrue(msg.startswith("refused: OLD occurs 2 times"), msg)

    def test_refuses_when_suite_red_before_mutation(self):
        (self.root / "impl.py").write_text("THRESHOLD = 9\n", encoding="utf-8")
        msg = receipt.make("99", "REQ-1.5", "impl.py", "impl.py", "THRESHOLD = 9", "THRESHOLD = 700", "x", self.cmd())
        self.assertTrue(msg.startswith("NOT WRITTEN: restored run exited 1"), msg)


if __name__ == "__main__":
    unittest.main(verbosity=1)
