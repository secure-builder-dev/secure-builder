# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""The command line. `python -m engine <command>`.

  check [--json]      run every mechanical check and the self-test suite — the
                      single command CI also runs (spec 01 REQ-3.1.1); needs no
                      credentials and no network (REQ-3.1.2)
  init ...            write the project configuration once (spec 01 §2)
  config              print the configuration and its problems
  degradation         print the honest-degradation statement (spec 04 §7)
  version             print the content-derived harness version
  update --project P [--dry-run]   place or refresh the harness in a project (spec 06)
  adopt --project P   adopt into an existing project and inventory pre-existing code
  ownership           print the four ownership classes
  audit               the standing self-test audit (spec 05 §10); reports, never blocks
  integration         run the integration tier with the real external tools (spec 05 §6.1)
  check --reverse-tests   run the self-test suite in reverse order (order independence)
  coverage            measure the harness's own self-test coverage (standard library only)
  credential-scan --staged   the credential check against the staged index, for a pre-commit hook
  accept-directive KEY "reason" "by"   accept a risky configuration directive into the baseline
  record <kind> k=v ...   append a record row: gate-log | finding | risk | changelog | started | supersede | rotate
  records             summarize the record set
  manifest            verify the control manifest and print recomputed call sites
  mutate              break every declared control, run the project's suite, restore (spec 01 §5.3)
  handoff [--checkpoint] [--scan-impossible "reason"]   generate the review handoff; writes the started marker
  gate prepare|submit|no-model ...   run the gates' mechanical parts; record a verdict block; or record a no-model run
  review unit=<u> run=<n>   launch the reviewer as a fresh process whose only input is the handoff (spec 03 §2.2)
  scan [--alarm] [--allow-unverified] [--skip-build]   run the five-concern scan, route findings, write the stamp
  scan bundle-images DIR | ingest-images DIR | bundle-data DIR | ingest-data DIR [--filtered-understood "why"]
  scan resolve id=<id> status=<fixed|carried|accepted> [note=...]   move an alarm finding; history appended
  currency [--offline]   report whether vendored catalogue pins are current — the only command that reaches the network
  catalogue ingest FILE [--acknowledge-markings] | bundle DIR | ingest-bundle DIR | list   adopt catalogues deliberately, with a diff
  governance show | propose | record change_id= file_section= grounding= approved_by=   the governance protocol (spec 01 §11)
  disposition checklist-line file=AGENTS.md section="## Project rules" text="..." source="[finding: F-1]"   append a grounded line
  probe [test_result="12 passed"]   capture the standing-state snapshot for HEAD and diff it against the previous gate's
  inventory           regenerate the coverage inventory (the assessed boundary)
  undeclared          regenerate the undeclared-controls list (the manifest completeness probe)
  status              orientation: position and exactly one next action (always exits 0)
  item new|claim|review|done ...     work items with a definition of done; unit new|building|review|merged
"""
import io
import json
import pathlib
import sys
import unittest

from . import config as cfgmod
from . import audit, coverage, degradation, distribute, integration, ownership, version
from .checks import run_all
from .outcome import Summary


def cmd_check(root, argv):
    as_json = "--json" in argv
    outcomes = []
    cfg = None
    try:
        cfg = cfgmod.load(root)
    except cfgmod.ConfigError:
        pass
    outcomes = run_all(root, cfg)
    for o in outcomes:
        for line in o.lines():
            print(line)
    summary = Summary(outcomes, na_threshold=cfg.na_threshold if cfg else 0.5)
    print(summary.line())
    for line in summary.disposition_lines():
        print(line)

    st = run_selftests(root, reverse="--reverse-tests" in argv)
    print(f"[selftest] {st['pass']} passed, {st['fail']} failed, {st['skip']} skipped"
          + (f" (skipped: {', '.join(st['skips'])})" if st["skips"] else ""))
    if st["pass"] + st["fail"] + st["skip"] == 0:
        print("[selftest] COULD NOT RUN: zero test cases discovered — an uninvoked suite is an absent suite")

    code = summary.exit_code
    if st["fail"] or (st["pass"] + st["fail"] + st["skip"] == 0):
        code = max(code, 1)
    if cfg:
        print(cfg.mode_line())
    print(f"harness version: {version()}")
    if as_json:
        print(json.dumps({
            "version": version(),
            "mode": cfg.mode if cfg else None,
            "checks": [{"check": o.check, "state": o.state.value, "blocking": o.blocking,
                        "findings": o.findings} for o in outcomes],
            "counts": {"applicable": summary.applicable, "not_applicable": summary.not_applicable,
                       "nothing_yet": summary.nothing_yet, "deferred": summary.deferred,
                       "failed": summary.failed},
            "selftest": st,
            "exit": code,
        }))
    print(f"check: {'GREEN' if code == 0 else 'RED'} (exit {code})")
    return code


SELFTEST_PATTERN = "test_*.py"


def discover_selftests(root):
    """The suite the check command runs. Discovery, not a hand-maintained list."""
    suite_dir = pathlib.Path(root) / "selftest"
    if not suite_dir.is_dir():
        return None
    return unittest.TestLoader().discover(str(suite_dir), pattern=SELFTEST_PATTERN, top_level_dir=str(root))


def _flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _flatten(item)
        else:
            yield item


def run_selftests(root, reverse=False):
    """Run the hermetic self-test suite and report pass/fail/skip separately (spec 05 REQ-9.4)."""
    suite = discover_selftests(root)
    if suite is None:
        return {"pass": 0, "fail": 0, "skip": 0, "skips": []}
    if reverse:
        suite = unittest.TestSuite(list(_flatten(suite))[::-1])
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=1).run(suite)
    failed = len(result.failures) + len(result.errors)
    for kind, items in (("FAIL", result.failures), ("ERROR", result.errors)):
        for test, tb in items:
            print(f"[selftest] {kind}: {test.id()}")
            print("    " + "\n    ".join(tb.strip().splitlines()[-4:]))
    skips = [t.id().split(".")[-1] for t, _ in result.skipped]
    return {"pass": result.testsRun - failed - len(result.skipped), "fail": failed,
            "skip": len(result.skipped), "skips": skips}


def cmd_init(root, argv):
    kw = {}
    for a in argv:
        if "=" in a:
            k, v = a.split("=", 1)
            kw[k.replace("-", "_")] = v
    if "track" not in kw or "mode" not in kw:
        print("init: track=<web|android> mode=<connected|local|disconnected> are required; "
              "optional: tier= provider= app_type= topology= side= operators= protected_branch= timezone= clock=")
        return 2
    try:
        cfg = cfgmod.init(root, **kw)
    except (cfgmod.ConfigError, TypeError) as e:
        print(f"init: REFUSED — {e}")
        return 1
    print(f"init: wrote {cfgmod.CONFIG_PATH}: {cfg.shape}; {cfg.mode_line()}")
    return 0


def cmd_config(root, argv):
    try:
        cfg = cfgmod.load(root)
    except cfgmod.ConfigError as e:
        print(f"config: {e}")
        return 1
    print(json.dumps(cfg.data, indent=2))
    for p in cfg.problems():
        print(f"problem: {p}")
    for a in cfg.unset_axes():
        print(f"not yet chosen: {a}")
    return 0


def cmd_degradation(root, argv):
    try:
        print(degradation.statement(root))
    except cfgmod.ConfigError as e:
        print(f"degradation: COULD NOT RUN — {e}")
        return 2
    return 0


def _project(root, argv):
    if "--project" in argv:
        return pathlib.Path(argv[argv.index("--project") + 1]).resolve()
    return root


def cmd_update(root, argv):
    project = _project(root, argv)
    if not project.is_dir():
        print(f"update: COULD NOT RUN — {project} is not a directory")
        return 2
    s = distribute.update(project, dry_run="--dry-run" in argv)
    for line in s.lines():
        print(line)
    print(f"update: project {project} carries harness version {distribute.recorded_version(project) or '(report only)'}")
    return 0


def cmd_adopt(root, argv):
    project = _project(root, argv)
    if not project.is_dir():
        print(f"adopt: COULD NOT RUN — {project} is not a directory")
        return 2
    s, n = distribute.adopt(project)
    for line in s.lines():
        print(line)
    print(f"adopt: {n} pre-existing file(s) inventoried as never assessed in "
          f"{ownership.ENGINE_DIR}/records/adoption-inventory.md; each needs a disposition")
    return 0


def cmd_audit(root, argv):
    from .checks import REGISTRY
    lines, total, could_not = audit.run(root, REGISTRY)
    for line in lines:
        print(line)
    return 2 if could_not else 0


def cmd_integration(root, argv):
    code, lines = integration.run(root)
    for line in lines:
        print(line)
    print(f"integration: {'PASSED' if code == 0 else 'NOT VERIFIED' if code == 2 else 'FAILED'} (exit {code})")
    return code


def cmd_coverage(root, argv):
    def suite():
        run_selftests(root)
    rep = coverage.collect(root, suite)
    tot = sum(v["total"] for v in rep["files"].values())
    cov = sum(v["covered"] for v in rep["files"].values())
    print(f"coverage: {cov}/{tot} executable lines ({(100.0 * cov / tot) if tot else 0:.1f}%) across {len(rep['files'])} harness modules -> .engine/local/coverage.json")
    return 0 if tot else 2


def cmd_credential_scan(root, argv):
    from .checks import credential_scan
    if "--staged" in argv:
        scanned, findings = credential_scan.scan_staged(root)
        for f in findings:
            print(f"    - {f}")
        print(f"[credential-scan] staged: {scanned} file(s), {len(findings)} finding(s)")
        return 1 if findings else 0
    o = credential_scan.run(root, None)
    for line in o.lines():
        print(line)
    return o.exit_code


def cmd_accept_directive(root, argv):
    from .checks import attack_surface
    if len(argv) < 3:
        print("accept-directive KEY \"reason\" \"by\" — KEY is path:kind as the check reports it")
        return 2
    attack_surface.accept(root, argv[0], argv[1], argv[2])
    print(f"accept-directive: {argv[0]} accepted by {argv[2]} — {argv[1]}")
    return 0


def _kv(argv):
    out = {}
    for a in argv:
        if "=" in a:
            k, v = a.split("=", 1)
            out[k] = v
    return out


def cmd_record(root, argv):
    from .records import changelog, findings, gatelog, table
    if not argv:
        print("record <gate-log|finding|risk|changelog|started|supersede|rotate> key=value ...")
        return 2
    kind, kv = argv[0], _kv(argv[1:])
    try:
        cfg = cfgmod.load(root)
    except cfgmod.ConfigError as e:
        print(f"record: COULD NOT RUN — {e}")
        return 2
    try:
        if kind == "gate-log":
            line = gatelog.append(root, cfg, **kv)
        elif kind == "finding":
            line = findings.add_check(root, cfg, id=kv["id"], finding_class=kv["class"], mechanism=kv["mechanism"],
                                      lives_in=kv["lives_in"], decided_by=kv["decided_by"], status=kv.get("status", "active"))
        elif kind == "risk":
            line = findings.add_risk(root, cfg, **{k: v for k, v in kv.items()})
        elif kind == "changelog":
            line = changelog.add(root, cfg, change_id=kv["change_id"], file_section=kv["file_section"],
                                 base_commit=kv["base_commit"], result_commit=kv.get("result_commit", "pending"),
                                 grounding=kv["grounding"], sign_off=kv["sign_off"],
                                 retroactive=kv.get("retroactive", "no") == "yes", rode_along=kv.get("rode_along", "-"))
        elif kind == "started":
            line = str(gatelog.write_started(root, cfg, kv["unit"], kv["run"], kv["range"], kv["head"]))
        elif kind == "supersede":
            line = gatelog.supersede(root, cfg, kv["unit"], kv["run"], kv["wrong"], kv["found"], kv["disposition"],
                                     kv["attested_by"], kv["reviewer"])
        elif kind == "rotate":
            n = gatelog.rotate(root, kv["period"])
            line = f"{n} row(s) rotated into gate-log.{kv['period']}.md"
        else:
            print(f"record: unknown kind {kind!r}")
            return 2
    except (table.Malformed, KeyError) as e:
        print(f"record: REFUSED — {e if not isinstance(e, KeyError) else 'missing ' + str(e)}")
        return 1
    print(f"record: {kind}: {line}")
    return 0


def cmd_records(root, argv):
    from .records import findings, gatelog
    rows, problems = gatelog.series(root)
    for p in problems:
        print(f"records: problem: {p}")
    print(f"records: gate log: {len(rows)} row(s) across {len(gatelog.series_files(root))} file(s); "
          f"{sum(1 for r in rows if r['_superseded'])} superseded; {len(gatelog.unmatched_markers(root))} started marker(s) without a row")
    for r in rows:
        mark = " [SUPERSEDED]" if r["_superseded"] else ""
        print(f"  {r['date']} {r['unit']}#{r['run']} {r['mode']} {r['verdict']} findings={r['findings']} "
              f"reviewer={r['reviewer']} ({r['reviewer_class']}) attested_by={r['attested_by']}{mark}")
    trend = []
    for r in rows:
        if r["verdict"] == "superseded":
            continue
        n = r["findings"].split(":")[0].strip()
        trend.append(f"{r['unit']}#{r['run']}={n}")
    if trend:
        print("records: findings per gate run (spec 01 REQ-12.3, trend): " + ", ".join(trend))
    a, b, _ = findings.read(root)
    print(f"records: findings register: {len(a)} permanent check(s), {len(b)} risk row(s)")
    return 0


def cmd_manifest(root, argv):
    from . import manifest
    try:
        state, results, structural = manifest.verify(root)
    except manifest.ManifestError as e:
        print(f"manifest: COULD NOT RUN — {e}")
        return 2
    print(f"manifest: {state}")
    for s_ in structural:
        print(f"  - {s_}")
    for r in results:
        sites = r["facts"].get("call_sites", [])
        print(f"  {r['id']} [{r['status']}{' / ' + r['counterpart'] if r['counterpart'] else ''}]: "
              f"{len(sites)} call site(s) recomputed, {len(r['facts'].get('tests', []))} test(s)"
              + (f"; problems: {'; '.join(r['problems'])}" if r["problems"] else ""))
        for site in sites[:5]:
            print(f"      called at {site}")
    return {"resolved": 0, "template-only": 0}.get(state, 1)


def cmd_mutate(root, argv):
    from . import manifest, mutate
    try:
        cfg = cfgmod.load(root)
        data = manifest.load(root)
    except (cfgmod.ConfigError, manifest.ManifestError) as e:
        print(f"mutate: COULD NOT RUN — {e}")
        return 2
    controls = manifest.real_controls(data)
    if not controls:
        print("mutate: NOTHING TO CHECK YET — the manifest declares no controls")
        return 0
    summary = mutate.run(root, cfg, controls)
    if "results" not in summary:
        print(f"mutate: COULD NOT RUN — {summary['reason']}")
        return 2
    for r in summary["results"]:
        print(f"  {r['control']} [{r['branch']}]: {r['verdict']} — {r['mutation']}")
    bad = [r for r in summary["results"] if r["verdict"] != "suite-failed"]
    print(f"mutate: {'FAIL' if bad else 'PASS'} — {len(summary['results']) - len(bad)} mutation(s) failed the suite, "
          f"{len(bad)} did not (a control whose mutation leaves the suite green is a blocking finding)")
    return 1 if bad else 0


def cmd_handoff(root, argv):
    from . import handoff
    try:
        cfg = cfgmod.load(root)
    except cfgmod.ConfigError as e:
        print(f"handoff: COULD NOT RUN — {e}")
        return 2
    reason = ""
    if "--scan-impossible" in argv:
        i = argv.index("--scan-impossible")
        reason = argv[i + 1] if i + 1 < len(argv) else ""
    try:
        doc = handoff.generate(root, cfg, checkpoint="--checkpoint" in argv, scan_impossible="--scan-impossible" in argv,
                               scan_impossible_reason=reason)
    except handoff.HandoffRefused as e:
        print(f"handoff: REFUSED — {e}")
        return 1
    p = handoff.write(root, doc)
    print(handoff.render(doc))
    print(f"handoff: written to {p.relative_to(root).as_posix()}")
    return 0


def cmd_gate(root, argv):
    from . import gate, gitutil
    if not argv:
        print("gate prepare unit=<u> run=<n> base=<sha> head=<sha> | gate submit unit= run= file=<verdict.json> attested_by= | gate no-model unit= run= attested_by=")
        return 2
    sub, kv = argv[0], _kv(argv[1:])
    try:
        cfg = cfgmod.load(root)
    except cfgmod.ConfigError as e:
        print(f"gate: COULD NOT RUN — {e}")
        return 2
    if sub == "prepare":
        unit, run = kv["unit"], kv["run"]
        base, head = gitutil.rev(root, kv["base"]), gitutil.rev(root, kv.get("head", "HEAD"))
        if not base or not head:
            print("gate: COULD NOT RUN — base/head do not resolve to commits")
            return 2
        q, s_, ctx = gate.prepare(root, cfg, unit, run, base, head)
        print(f"gate: quality gate on {base[:12]}..{head[:12]}")
        for o in q:
            for line in o.lines():
                print("  " + line)
        if not any(o.failed for o in q):
            print("gate: quality gate PASSED; security gate mechanical part:")
            for o in s_:
                for line in o.lines():
                    print("  " + line)
            print(f"gate: checklist for the reviewer written to .engine/local/gate-{unit}-{run}-checklist.md "
                  f"(version {ctx['checklist_version']}; control-shaped: {'yes' if ctx['control_shaped'] else 'no'})")
            return 1 if any(o.failed for o in s_) else 0
        print("gate: quality gate FAILED; the security gate does not run on code whose tests do not pass (REQ-6.1.4)")
        return 1
    if sub == "submit":
        try:
            v = json.loads(pathlib.Path(kv["file"]).read_text(encoding="utf-8"))
        except (KeyError, OSError, ValueError) as e:
            print(f"gate: COULD NOT RUN — verdict file unreadable ({e})")
            return 2
        line, probs = gate.submit(root, cfg, kv["unit"], kv["run"], v, kv.get("attested_by", ""))
        if probs:
            print("gate: verdict REFUSED")
            for p in probs:
                print("  - " + p)
            return 1
        print(f"gate: recorded {line}")
        return 0
    if sub == "no-model":
        line, probs = gate.no_model(root, cfg, kv["unit"], kv["run"], kv.get("attested_by", ""))
        if probs:
            print("gate: REFUSED — " + "; ".join(probs))
            return 1
        print(f"gate: recorded advisory row (no model; checklist not applied): {line}")
        return 0
    print(f"gate: unknown subcommand {sub!r}")
    return 2


def cmd_review(root, argv):
    """Structural isolation: a new process, started from nothing, handed the path of the
    generated handoff as its only argument. The reviewer command comes from the environment
    (ENGINE_REVIEWER_CMD), never from the repository; the construction conversation is
    not available to the new process by construction."""
    import os
    import shlex
    import subprocess
    kv = _kv(argv)
    p = pathlib.Path(root) / ".engine" / "local" / f"handoff-{kv.get('unit', '')}-{kv.get('run', '')}.md"
    if not p.is_file():
        print(f"review: COULD NOT RUN — no handoff at {p.relative_to(root).as_posix()}; generate it first")
        return 2
    cmd = os.environ.get("ENGINE_REVIEWER_CMD", "")
    if not cmd.strip():
        print("review: COULD NOT RUN — ENGINE_REVIEWER_CMD is not set; it names the reviewer CLI and lives outside the repository")
        return 2
    from . import tools
    args = shlex.split(cmd) + [str(p)]   # the handoff artifact is the only input
    exe = tools.resolve(args[0])
    if not exe:
        print(f"review: COULD NOT RUN — reviewer '{args[0]}' is not on the search path")
        return 2
    args[0] = exe
    env = {k: v for k, v in os.environ.items() if not k.startswith("ENGINE_SESSION")}
    res = subprocess.run(args, cwd=str(root), env=env)
    print(f"review: reviewer process exited {res.returncode}; submit its verdict block with `gate submit`")
    return res.returncode


def cmd_scan(root, argv):
    from .scan import alarm, bundles, runner
    try:
        cfg = cfgmod.load(root)
    except cfgmod.ConfigError as e:
        print(f"scan: COULD NOT RUN — {e}")
        return 2
    sub = argv[0] if argv and not argv[0].startswith("--") else ""
    kv = _kv(argv)
    operator = kv.get("operator") or cfg.get("operator") or "unnamed operator"
    try:
        if sub in ("bundle-images", "bundle-data", "ingest-images", "ingest-data"):
            d = argv[1]
            if sub == "bundle-images":
                data = bundles.bundle_images(root, d, cfg, operator)
            elif sub == "bundle-data":
                data = bundles.bundle_data(root, d, cfg, operator)
            else:
                reason = ""
                if "--filtered-understood" in argv:
                    reason = argv[argv.index("--filtered-understood") + 1]
                data = bundles.ingest(root, d, cfg, operator, filtered_understood=reason)
            print(f"scan: {sub}: {data['bundle_id']} produced {data['produced']} by {data.get('operator')} on side {data.get('source_side')}")
            return 0
        if sub == "resolve":
            v = alarm.resolve(root, cfg, kv["id"], kv["status"], kv.get("note", ""))
            print(f"scan: {kv['id']} -> {v['status']}; history: {v['status_history']}")
            return 0
        if cfg.mode == "disconnected":
            missing = bundles.images_present()
            if missing:
                print("scan: COULD NOT RUN — disconnected mode uses only images already present:")
                for m_ in missing:
                    print("  - " + m_)
                return 2
        sc = runner.Scan(root, cfg)
        result = sc.run(allow_unverified="--allow-unverified" in argv, skip_build="--skip-build" in argv)
    except (runner.ScanError, RuntimeError, ValueError, KeyError, IndexError) as e:
        print(f"scan: COULD NOT RUN — {e}")
        return 2
    print(f"scan: engine={sc.engine}; mode={cfg.mode}; scanners ran: {', '.join(result['ran']) or 'none'}"
          + (f"; detection data {result['data_age']} day(s) old" if result["data_age"] is not None else ""))
    for p_ in result["problems"]:
        print(f"  - {p_}")
    for f in result["actionable"]:
        print(f"  actionable: {f.line()}")
    for f in result["carried"]:
        print(f"  carried: {f.line()}")
    for a in result["aged"]:
        print(f"  aged: {a}")
    if "--alarm" in argv:
        raised = alarm.raise_alarms(root, cfg, result["findings"] + result["informational"])
        print(f"scan: standing alarm {result['alarm'].upper()}; {len(raised)} new finding(s) recorded with owner, triage window and work item")
        for ident, first, resolved, days in alarm.intervals(root):
            print(f"  {ident}: detected {first}, {'resolved ' + resolved if resolved else 'open'}, {days} day(s)")
    print(f"scan: gate verdict {result['verdict'].upper()} for {result['head'][:12]}; stamp written")
    return {"green": 0, "unverified": 3}.get(result["verdict"], 1)


def cmd_currency(root, argv):
    from . import catalogue
    try:
        cfg = cfgmod.load(root)
    except cfgmod.ConfigError as e:
        print(f"currency: COULD NOT RUN — {e}")
        return 2
    lines, code = catalogue.currency(root, cfg, offline="--offline" in argv)
    for line in lines:
        print(line)
    return code


def cmd_catalogue(root, argv):
    from . import catalogue
    if not argv:
        print("catalogue ingest FILE [--acknowledge-markings] | bundle DIR | ingest-bundle DIR | list")
        return 2
    sub = argv[0]
    try:
        if sub == "list":
            for key, c in catalogue.load_all(root).items():
                p = c["_provenance"]
                print(f"{key}: {p['version']}; {len(c['entries'])} entries; source {p['source']}; retrieved {p['retrieved']}; {p['redistribution']}")
            return 0
        if sub == "ingest":
            d = catalogue.ingest(root, argv[1], acknowledge_markings="--acknowledge-markings" in argv)
            print(f"catalogue: adopted {argv[1]}; {len(d)} change(s) against the previous version:")
            for line in d:
                print("  " + line)
            return 0
        if sub == "bundle":
            m_ = catalogue.bundle(root, argv[1])
            print(f"catalogue: bundle produced {m_['produced']} with {len(m_['catalogues'])} catalogue(s); sha256 {m_['sha256'][:12]}…")
            return 0
        if sub == "ingest-bundle":
            diffs = catalogue.ingest_bundle(root, argv[1])
            for key, d in diffs.items():
                print(f"catalogue: {key}: {len(d)} change(s)")
                for line in d:
                    print("  " + line)
            return 0
    except (catalogue.CatalogueError, OSError, ValueError, IndexError) as e:
        print(f"catalogue: REFUSED — {e}")
        return 1
    print(f"catalogue: unknown subcommand {sub!r}")
    return 2


def cmd_governance(root, argv):
    from . import governance
    sub, kv = (argv[0] if argv else ""), _kv(argv[1:])
    try:
        cfg = cfgmod.load(root)
    except cfgmod.ConfigError as e:
        print(f"governance: COULD NOT RUN — {e}")
        return 2
    if sub == "show":
        print("governed set (human-authored only, except allowlisted zones):")
        for g in governance.governed_set(root, cfg):
            print(f"  {g}")
        print("agent-editable zones (append grounded entries only):")
        for z in governance.zones(root):
            print(f"  {z['file']} {z['section']}")
        probs = governance.staged_problems(root, cfg)
        for p in probs:
            print(f"staged: {p}")
        return 0
    if sub == "propose":
        text = governance.staged_diff(root, governance.governed_set(root, cfg))
        if not text.strip():
            print("governance: no governed file is staged")
            return 1
        print("governance: the literal text being changed — shown in the request itself, never behind a detail:")
        print(text)
        print("governance: record approval with `governance record change_id= file_section= grounding= approved_by=`; the row records this text")
        return 0
    if sub == "record":
        try:
            shown = governance.staged_diff(root, governance.governed_set(root, cfg)) or kv.get("shown", "")
            line = governance.record(root, cfg, change_id=kv["change_id"], file_section=kv["file_section"], grounding=kv["grounding"],
                                     shown_text=shown, approved_by=kv["approved_by"])
        except KeyError as e:
            print(f"governance: REFUSED — missing {e}")
            return 1
        except Exception as e:
            print(f"governance: REFUSED — {e}")
            return 1
        print(f"governance: row written before the commit: {line}")
        return 0
    print("governance show | propose | record change_id= file_section= grounding= approved_by=")
    return 2


def cmd_disposition(root, argv):
    from . import governance
    sub, kv = (argv[0] if argv else ""), _kv(argv[1:])
    if sub != "checklist-line":
        print("disposition checklist-line file= section= text= source=")
        return 2
    try:
        entry = governance.append_grounded(root, kv.get("file", "AGENTS.md"), kv.get("section", "## Project rules"), kv["text"], kv["source"])
    except (PermissionError, KeyError, OSError) as e:
        print(f"disposition: REFUSED — {e}")
        return 1
    print(f"disposition: appended to {kv.get('file', 'AGENTS.md')} {kv.get('section', '## Project rules')}: {entry}")
    return 0


def cmd_probe(root, argv):
    from . import gitutil, probes
    try:
        cfg = cfgmod.load(root)
    except cfgmod.ConfigError as e:
        print(f"probe: COULD NOT RUN — {e}")
        return 2
    head = gitutil.head(root)
    if not head:
        print("probe: COULD NOT RUN — no commit")
        return 2
    o = probes.run_probe(root, cfg, head, _kv(argv).get("test_result"))
    for line in o.lines():
        print(line)
    return o.exit_code


def cmd_inventory(root, argv):
    from . import probes
    try:
        cfg = cfgmod.load(root)
    except cfgmod.ConfigError:
        cfg = None
    rows, counts = probes.write_inventory(root, cfg)
    print(f"inventory: {counts['assessed']} assessed, {counts['never']} never assessed, {counts['elsewhere']} assessed elsewhere "
          f"(evidence not available) -> {probes.INVENTORY}")
    return 0


def cmd_undeclared(root, argv):
    from . import probes
    o = probes.completeness_probe(root, None)
    for line in o.lines():
        print(line)
    return 0


def cmd_status(root, argv):
    from . import lifecycle
    try:
        cfg = cfgmod.load(root)
    except cfgmod.ConfigError:
        cfg = None
    for line in lifecycle.orient(root, cfg):
        print(line)
    return 0


def cmd_item(root, argv):
    from . import lifecycle
    if not argv:
        print("item new id=<id> unit=<unit> done_when=\"...\" [depends_on=a,b] | item claim|review|done id=<id> | unit new|building|review|merged id=<unit>")
        return 2
    sub, kv = argv[0], _kv(argv[1:])
    try:
        if sub == "new":
            deps = [d for d in kv.get("depends_on", "").split(",") if d]
            p = lifecycle.create_item(root, kv["id"], kv["unit"], kv.get("done_when", ""), deps)
            print(f"item: created {p.relative_to(root).as_posix()}")
        elif sub in ("claim", "review", "done"):
            st = {"claim": "claimed", "review": "in review", "done": "done"}[sub]
            print(f"item: {kv['id']} -> {lifecycle.transition_item(root, kv['id'], st)}")
        else:
            print(f"item: unknown subcommand {sub!r}")
            return 2
    except (ValueError, KeyError) as e:
        print(f"item: REFUSED — {e}")
        return 1
    return 0


def cmd_unit(root, argv):
    from . import lifecycle
    sub, kv = (argv[0] if argv else ""), _kv(argv[1:])
    try:
        if sub == "new":
            p = lifecycle.create_unit(root, kv["id"])
            print(f"unit: created {p.relative_to(root).as_posix()}")
        elif sub in ("building", "review", "merged"):
            st = {"building": "building", "review": "in review", "merged": "merged"}[sub]
            print(f"unit: {kv['id']} -> {lifecycle.transition_unit(root, kv['id'], st)}")
        else:
            print("unit new|building|review|merged id=<unit>")
            return 2
    except (ValueError, KeyError) as e:
        print(f"unit: REFUSED — {e}")
        return 1
    return 0


def cmd_ownership(root, argv):
    for name, table in ownership.classes():
        print(f"## {name}")
        for k in (table if isinstance(table, list) else table):
            print(f"  {k}")
    return 0


COMMANDS = {"check": cmd_check, "init": cmd_init, "config": cmd_config,
            "degradation": cmd_degradation, "version": lambda r, a: (print(version()), 0)[1],
            "update": cmd_update, "adopt": cmd_adopt, "ownership": cmd_ownership,
            "audit": cmd_audit, "integration": cmd_integration, "coverage": cmd_coverage,
            "credential-scan": cmd_credential_scan, "accept-directive": cmd_accept_directive,
            "record": cmd_record, "records": cmd_records, "manifest": cmd_manifest, "mutate": cmd_mutate,
            "handoff": cmd_handoff, "gate": cmd_gate, "status": cmd_status, "item": cmd_item, "unit": cmd_unit,
            "review": cmd_review, "scan": cmd_scan, "currency": cmd_currency, "catalogue": cmd_catalogue,
            "governance": cmd_governance, "disposition": cmd_disposition, "probe": cmd_probe,
            "inventory": cmd_inventory, "undeclared": cmd_undeclared}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    root = pathlib.Path(".").resolve()
    if "--root" in argv:
        i = argv.index("--root")
        root = pathlib.Path(argv[i + 1]).resolve()
        del argv[i:i + 2]
    if not argv or argv[0] not in COMMANDS:
        print(__doc__)
        return 2
    return COMMANDS[argv[0]](root, argv[1:])


if __name__ == "__main__":
    sys.exit(main())
