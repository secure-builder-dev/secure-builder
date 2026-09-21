# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Distribution, ownership and upgrade (spec 06)."""
import json
import pathlib
import unittest

from engine import distribute, ownership as own
from engine.checks import divergence
from engine.outcome import State
from .helpers import ROOT, cli, find_line, git, git_repo, tree, write, write_config

RULES = f"{own.ENGINE_DIR}/rules/RULES.md"
SEED_FILES = sum(len(list(distribute._source_files(ROOT, src))) for src in own.SEED_IF_ABSENT.values())


class Classes(unittest.TestCase):
    def test_four_classes_enumerated_including_project_owned(self):
        names = [n for n, _ in own.classes()]
        self.assertEqual(names, ["engine-owned", "seed-if-absent", "engine-reference", "project-owned"])
        self.assertGreater(len(own.PROJECT_OWNED), 0, "project-owned paths must be enumerated too")
        self.assertIn(f"{own.ENGINE_DIR}/records/", own.PROJECT_OWNED)

    def test_every_source_exists(self):
        # in the build tree every source exists beside engine/; in a placed copy (.engine/harness/) a source
        # outside the package, such as reviewers/, exists only as its placed target under .engine/
        for table in (own.ENGINE_OWNED, own.SEED_IF_ABSENT, own.ENGINE_REFERENCE):
            for target, src in table.items():
                self.assertTrue((ROOT / src).exists() or (ROOT.parent.parent / target).exists(),
                                f"{target} -> {src} does not exist in the harness tree")

    def test_class_of(self):
        self.assertEqual(own.class_of(f"{own.ENGINE_DIR}/rules/RULES.md"), "engine-owned")
        self.assertEqual(own.class_of(f"{own.ENGINE_DIR}/rules/agents/x.md"), "engine-owned")
        self.assertEqual(own.class_of("AGENTS.md"), "seed-if-absent")
        self.assertEqual(own.class_of(f"{own.ENGINE_DIR}/rules/control-manifest.json"), "seed-if-absent",
                         "the control manifest is seeded once and never overwritten by tooling")
        self.assertEqual(own.class_of(f"{own.ENGINE_DIR}/records/gate-log.md"), "seed-if-absent")
        self.assertEqual(own.class_of("plans/x.md"), "project-owned")
        self.assertIsNone(own.class_of("something/else"))

    def test_engine_reference_is_small(self):
        self.assertLessEqual(len(own.ENGINE_REFERENCE), 5, "engine-reference must stay a handful of files")

    def test_every_engine_owned_source_carries_marker(self):
        for target, src in own.ENGINE_OWNED.items():
            for sub, p in distribute._source_files(ROOT, src):
                if own.marker_required(p.relative_to(ROOT)):
                    self.assertIn(own.ENGINE_OWNED_MARKER, p.read_text(encoding="utf-8"), str(p))
        self.assertTrue(own.marker_required("engine/gate.py"))
        self.assertFalse(own.marker_required("engine/dist/templates/AGENTS.md"))


class Update(unittest.TestCase):
    def test_places_all_classes_and_records_version(self):
        with tree() as t:
            s = distribute.update(t)
            self.assertTrue((t / RULES).is_file())
            self.assertTrue((t / own.ENGINE_DIR / "harness/engine/outcome.py").is_file())
            self.assertTrue((t / "AGENTS.md").is_file())
            self.assertTrue((t / own.reference_path("AGENTS.md")).is_file())
            self.assertEqual(own.reference_path("AGENTS.md"), ".engine/harness/seeds/AGENTS.md")
            self.assertEqual(own.reference_path(".engine/rules/governance.json"), ".engine/harness/seeds/governance.json")
            self.assertEqual(own.reference_path(".engine/records/gate-log.md"), ".engine/harness/seeds/records/gate-log.md")
            v = (t / own.VERSION_FILE).read_text().splitlines()
            self.assertRegex(v[0], r"^\d+\.\d+\.\d+\S*\+[0-9a-f]{12}$")
            self.assertRegex(v[1], r"^\d{4}-\d{2}-\d{2}$")
            self.assertEqual(s.by_class["seed-if-absent"], {"seeded": SEED_FILES})
            self.assertEqual(s.diverged, [])
            self.assertEqual(s.removed, [])

    def test_idempotent(self):
        with tree() as t:
            distribute.update(t)
            before = {p: p.read_bytes() for p in t.rglob("*") if p.is_file()}
            s = distribute.update(t)
            after = {p: p.read_bytes() for p in t.rglob("*") if p.is_file()}
            self.assertEqual(before, after)
            self.assertEqual(s.diverged, [])
            self.assertNotIn("overwritten", s.by_class["engine-owned"])
            self.assertEqual(s.by_class["seed-if-absent"], {"already present": SEED_FILES})

    def test_engine_owned_overwritten_with_backup_and_report(self):
        with tree() as t:
            distribute.update(t)
            write(t, RULES, "# my local edit\n")
            s = distribute.update(t)
            self.assertEqual((t / RULES).read_bytes(), (ROOT / "engine/dist/rules/RULES.md").read_bytes())
            self.assertEqual((t / (RULES + own.BACKUP_SUFFIX)).read_text(), "# my local edit\n")
            self.assertEqual(s.diverged, [(RULES, RULES + own.BACKUP_SUFFIX)])
            self.assertTrue(any(l.startswith("  diverged (1)") for l in s.lines()), s.lines())
            self.assertIn(f"    - {RULES} -> {RULES}{own.BACKUP_SUFFIX}", s.lines())

    def test_seed_if_absent_left_byte_identical(self):
        with tree() as t:
            write(t, "AGENTS.md", "mine\n")
            s = distribute.update(t)
            self.assertEqual((t / "AGENTS.md").read_text(), "mine\n")
            self.assertEqual(s.by_class["seed-if-absent"]["already present"], 1)
            self.assertEqual(s.by_class["seed-if-absent"]["seeded"], SEED_FILES - 1)

    def test_project_owned_never_touched(self):
        with tree() as t:
            write(t, f"{own.ENGINE_DIR}/records/gate-log.md", "| my | rows |\n")
            write(t, f"{own.ENGINE_DIR}/records/stale-thing.md", "keep me\n")
            write(t, "plans/plan.md", "plan\n")
            distribute.update(t)
            self.assertEqual((t / own.ENGINE_DIR / "records/gate-log.md").read_text(), "| my | rows |\n")
            self.assertTrue((t / own.ENGINE_DIR / "records/stale-thing.md").is_file())
            self.assertEqual((t / "plans/plan.md").read_text(), "plan\n")

    def test_dry_run_changes_nothing_and_says_so(self):
        with tree() as t:
            s = distribute.update(t, dry_run=True)
            self.assertEqual([p for p in t.rglob("*")], [])
            self.assertEqual(s.lines()[0], "update: REPORT ONLY — nothing changed")
            self.assertEqual(s.by_class["seed-if-absent"], {"seeded": SEED_FILES})

    def test_no_version_control_action_and_dirty_tree_ok(self):
        with tree() as t:
            git_repo(t)
            write(t, "dirty.txt", "uncommitted\n")
            distribute.update(t)
            status = git(t, "status", "--porcelain").stdout
            self.assertIn("?? dirty.txt", status)
            self.assertEqual(git(t, "log", "--oneline").stdout.strip(), "", "update must not commit")

    def test_summary_grouped_by_class_with_counts(self):
        with tree() as t:
            s = distribute.update(t)
            lines = s.lines()
            self.assertTrue(find_line(lines, "  engine-owned: ").endswith("written"))
            find_line(lines, "  seed-if-absent: ")
            find_line(lines, "  engine-reference: ")
            self.assertEqual(find_line(lines, "  project-owned: "), f"  project-owned: {len(own.PROJECT_OWNED)} untouched")

    def test_reference_copy_not_read_by_any_check(self):
        import re
        pattern = re.compile(re.escape(own.REFERENCE_DIR) + r"|harness/seeds|reference_path")
        for p in (ROOT / "engine").rglob("*.py"):
            if p.name in ("ownership.py", "distribute.py"):
                continue
            self.assertIsNone(pattern.search(p.read_text(encoding="utf-8")),
                              f"{p.name} references the seeds directory")


class FourFolders(unittest.TestCase):
    def test_every_placed_path_is_under_rules_harness_records_or_work(self):
        # the layout rule: everything the engine places or writes sits in one of four folders
        ok = (f"{own.ENGINE_DIR}/rules/", f"{own.ENGINE_DIR}/harness/", f"{own.ENGINE_DIR}/records/", f"{own.ENGINE_DIR}/work/")
        for table in (own.ENGINE_OWNED, own.SEED_IF_ABSENT, own.ENGINE_REFERENCE):
            for target in table:
                if target == "AGENTS.md" or target == f"{own.ENGINE_DIR}/.gitignore":
                    continue          # the project's instruction file, and the folder's own gitignore
                self.assertTrue(target.startswith(ok), target)
        for target in own.PROJECT_OWNED:
            if target.startswith(own.ENGINE_DIR):
                self.assertTrue(target.startswith(ok), target)
        for const in (own.VERSION_FILE, own.PLACED_MANIFEST, own.TRACKING_RECORD, own.REFERENCE_DIR):
            self.assertTrue(const.startswith(ok), const)

    def test_a_project_on_the_old_layout_is_moved_not_duplicated(self):
        from .helpers import commit, git, git_repo, write_config
        NL = chr(10)
        with tree() as t:
            write_config(t)
            git_repo(t)
            # an old-layout project: config beside .engine, a record in local/, a reviewer definition in agents/
            (t / ".engine" / "rules" / "config.json").rename(t / ".engine" / "config.json")
            write(t, ".engine/local/handoff-U-1.md", "# GATE HANDOFF: U run 1" + NL)
            write(t, ".engine/agents/mine.md", "project reviewer" + NL)
            write(t, "AGENTS.md.engine-reference", "old reference copy" + NL)
            git(t, "add", "-A"); commit(t)
            s = distribute.update(t)
            moved = dict(s.migrated)
            self.assertEqual(moved[".engine/config.json"], ".engine/rules/config.json")
            self.assertEqual(moved[".engine/local"], ".engine/work")
            self.assertEqual(moved["AGENTS.md.engine-reference"], ".engine/harness/seeds/AGENTS.md")
            self.assertTrue((t / ".engine/work/handoff-U-1.md").is_file())
            self.assertTrue((t / ".engine/rules/agents/mine.md").is_file(), "a project's own definition moves with the folder")
            self.assertFalse((t / ".engine/local").exists())
            self.assertFalse((t / ".engine/config.json").exists())
            status = git(t, "status", "--short").stdout
            self.assertIn("R  .engine/local/handoff-U-1.md -> .engine/work/handoff-U-1.md", status, "version control sees a rename")
            self.assertEqual(distribute.update(t).migrated, [], "a second update has nothing to move")


class AgentTracking(unittest.TestCase):
    def test_tracking_record_written_beside_definitions(self):
        with tree() as t:
            distribute.update(t)
            rec = (t / own.TRACKING_RECORD).read_text().splitlines()
            self.assertTrue(rec[0].startswith("#"))
            self.assertIn("README.md", rec)

    def test_retired_definition_removed_project_definition_kept(self):
        with tree() as t:
            distribute.update(t)
            agents = t / own.ENGINE_DIR / "rules" / "agents"
            write(t, f"{own.ENGINE_DIR}/rules/agents/retired.md", "old reviewer\n")
            write(t, f"{own.ENGINE_DIR}/rules/agents/mine.md", "project reviewer\n")
            with (t / own.TRACKING_RECORD).open("a") as f:
                f.write("retired.md\n")
            s = distribute.update(t)
            self.assertFalse((agents / "retired.md").exists(), "a retired engine-placed definition must be removed")
            self.assertTrue((agents / "mine.md").exists(), "a project's own definition must be left alone")
            self.assertIn(f"{own.ENGINE_DIR}/rules/agents/retired.md", s.removed)

    def test_tracking_entries_with_separators_ignored(self):
        self.assertEqual(distribute.valid_tracking_entries(
            ["# comment", "good.md", "../evil.md", "sub/dir.md", "..", "bad\\path.md", ""]), ["good.md"])

    def test_traversal_entry_deletes_nothing(self):
        with tree() as t:
            distribute.update(t)
            write(t, "victim.md", "outside agents\n")
            with (t / own.TRACKING_RECORD).open("a") as f:
                f.write("../../victim.md\n")
            distribute.update(t)
            self.assertTrue((t / "victim.md").is_file())


class Divergence(unittest.TestCase):
    def test_clean_after_update(self):
        with tree() as t:
            write_config(t)
            distribute.update(t)
            o = divergence.run(t, None)
            self.assertIs(o.state, State.CLEAN, o.line())
            self.assertRegex(o.line(), r"^\[engine-divergence\] CLEAN: \d+ engine-owned files match version ")

    def test_edited_engine_owned_file_is_blocking(self):
        with tree() as t:
            distribute.update(t)
            write(t, RULES, "# edited\n")
            o = divergence.run(t, None)
            self.assertIs(o.state, State.FINDINGS)
            self.assertTrue(o.blocking)
            self.assertEqual(o.findings, [f"{RULES}: differs from the copy version " + distribute.recorded_version(t) + " placed"])

    def test_missing_engine_owned_file_reported(self):
        with tree() as t:
            distribute.update(t)
            (t / RULES).unlink()
            o = divergence.run(t, None)
            self.assertIn(f"{RULES}: missing (placed by version {distribute.recorded_version(t)})", o.findings)

    def test_never_placed_is_could_not_run(self):
        with tree() as t:
            o = divergence.run(t, None)
            self.assertIs(o.state, State.COULD_NOT_RUN)

    def test_empty_placed_manifest_is_not_a_pass(self):
        with tree() as t:
            write(t, own.PLACED_MANIFEST, json.dumps({"version": "x", "files": {}}))
            o = divergence.run(t, None)
            self.assertIs(o.state, State.COULD_NOT_RUN)
            self.assertIn("nothing to compare is not a pass", o.detail)

    def test_harness_source_tree_is_not_applicable_with_coverage(self):
        o = divergence.run(ROOT, None)
        self.assertIs(o.state, State.NOT_APPLICABLE)
        self.assertIn("engine.version()", o.covers)


class Adopt(unittest.TestCase):
    def test_adoption_inventories_preexisting_files_and_touches_no_source(self):
        with tree() as t:
            git_repo(t)
            write(t, "src/app.py", "print('hi')\n")
            write(t, "README.md", "# old project\n")
            git(t, "add", "-A"); git(t, "commit", "-q", "-m", "pre-harness")
            s, n = distribute.adopt(t)
            self.assertEqual(n, 2)
            self.assertEqual((t / "src/app.py").read_text(), "print('hi')\n")
            inv = (t / own.ENGINE_DIR / "records/adoption-inventory.md").read_text()
            self.assertIn("| src/app.py |  |  |", inv)
            self.assertIn("| README.md |  |  |", inv)
            self.assertIn("never passed a gate", inv)

    def test_adoption_does_not_require_checks_to_pass(self):
        with tree() as t:
            git_repo(t)
            write(t, "src/app.py", "password = 'hunter2'\n")
            git(t, "add", "-A"); git(t, "commit", "-q", "-m", "x")
            s, n = distribute.adopt(t)
            self.assertEqual(n, 1)

    def test_adoption_inventory_never_regenerated(self):
        with tree() as t:
            git_repo(t)
            write(t, "src/app.py", "x\n")
            git(t, "add", "-A"); git(t, "commit", "-q", "-m", "x")
            distribute.adopt(t)
            inv = t / own.ENGINE_DIR / "records/adoption-inventory.md"
            inv.write_text(inv.read_text().replace("| src/app.py |  |  |", "| src/app.py | reviewed | ok |"))
            distribute.adopt(t)
            self.assertIn("| src/app.py | reviewed | ok |", inv.read_text())


class Cli(unittest.TestCase):
    def test_update_command_reports_version(self):
        with tree() as t:
            code, lines = cli(t, "update", "--project", str(t))
            self.assertEqual(code, 0)
            find_line(lines, "update: applied")
            self.assertRegex(find_line(lines, "update: project "), r"carries harness version \d+\.\d+\.\d+\S*\+[0-9a-f]{12}$")

    def test_ownership_command_lists_four_classes(self):
        code, lines = cli(ROOT, "ownership")
        self.assertEqual([l for l in lines if l.startswith("## ")],
                         ["## engine-owned", "## seed-if-absent", "## engine-reference", "## project-owned"])


class InstructionFileSplit(unittest.TestCase):
    """Spec 06 §4 and spec 03 §1.2, §1.1.4, §5."""
    TEMPLATE = ROOT / "engine/dist/templates/AGENTS.md"
    RULES_SRC = ROOT / "engine/dist/rules/RULES.md"

    def test_instruction_file_imports_rules_by_stable_engine_owned_path(self):
        text = self.TEMPLATE.read_text(encoding="utf-8")
        line = [l for l in text.splitlines() if l.startswith("Read and follow: ")]
        self.assertEqual(len(line), 1, "the seeded instruction file must import the rulebook exactly once")
        path = line[0].split(": ", 1)[1].strip()
        self.assertEqual(own.class_of(path), "engine-owned", f"{path} must be an engine-owned path")
        self.assertIn("## Project rules", text.splitlines())

    def test_instruction_file_states_precedence_and_that_it_is_not_a_control(self):
        lines = self.TEMPLATE.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len([l for l in lines if "wins over this file" in l]), 1)
        self.assertEqual(len([l for l in lines if "no enforcement" in l]), 1)

    def test_rulebook_states_precedence_and_that_it_is_not_a_control(self):
        lines = self.RULES_SRC.read_text(encoding="utf-8").splitlines()
        self.assertIn("## Precedence", lines)
        self.assertEqual(len([l for l in lines if "carries no enforcement" in l]), 1)

    def test_rulebook_forbids_reading_environment_secrets(self):
        lines = self.RULES_SRC.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len([l for l in lines if "never read or reproduce environment secrets" in l]), 1)

    def test_rulebook_uses_no_references_of_its_own(self):
        for l in self.RULES_SRC.read_text(encoding="utf-8").splitlines():
            self.assertFalse(l.startswith(("Read and follow:", "@", "import ")),
                             f"an included file must not reference further files: {l!r}")

    def test_rulebook_is_short_and_states_only_the_three_things(self):
        lines = self.RULES_SRC.read_text(encoding="utf-8").splitlines()
        self.assertLess(len(lines), 120, "the always-loaded rules must stay short")
        for h in ("## Non-negotiables", "## Where things live", "## Lifecycle"):
            self.assertIn(h, lines)

    def test_changes_note_placed_engine_owned(self):
        with tree() as t:
            distribute.update(t)
            p = t / own.ENGINE_DIR / "harness" / "CHANGES.md"
            self.assertTrue(p.is_file())
            self.assertIn("# Changes that newly fail", p.read_text(encoding="utf-8"))


class NeverAutomatic(unittest.TestCase):
    def test_check_never_updates(self):
        with tree() as t:
            write_config(t)
            distribute.update(t)
            write(t, "selftest/__init__.py", "")     # a fixture suite so the check does not run the placed one here
            write(t, "selftest/test_fx.py", "import unittest" + chr(10) + "class T(unittest.TestCase):" + chr(10) + "    def test_ok(self): pass" + chr(10))
            write(t, RULES, "# edited locally\n")
            code, lines = cli(t, "check")
            self.assertEqual((t / RULES).read_text(), "# edited locally\n",
                             "the check command must report divergence, never repair it")
            find_line(lines, "[engine-divergence] FINDINGS BLOCKING")
