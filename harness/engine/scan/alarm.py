# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""The standing alarm and its lifecycle (spec 01 §4.6.1, §4.10.1–4.10.2).

The alarm fires on a schedule against code that is already merged and running.
Every alarm finding has a disposition path — an owner, a triage window, and a
work item that enters the ordinary lifecycle — and a durable record, so the
interval between detection and remediation is measurable. Status changes are
new rows with an appended history; nothing is edited or deleted.
"""
import datetime
import pathlib

from .. import lifecycle
from ..records import table
from ..records import schema as sch
from .runner import CARRIED_RECORD, HIGH

STATUSES = ("detected", "fixed", "carried", "accepted")


def latest_rows(root):
    rows, _, _ = table.read(root, CARRIED_RECORD, "carried-findings")
    latest = {}
    for r in rows or []:
        latest[r["id"]] = r
    return latest


def raise_alarms(root, cfg, findings):
    """Durable records and work items for every high/critical finding not already tracked."""
    owner = (cfg.get("scan_owner") if cfg else None) or "unassigned"
    days = int((cfg.get("alarm_triage_days") if cfg else None) or 7)
    today = datetime.date.today()
    latest = latest_rows(root)
    raised = []
    for f in findings:
        if f.severity not in HIGH:
            continue
        ident = f"{f.id}/{f.package}"
        if ident in latest and latest[ident]["status"] in ("detected", "carried", "accepted"):
            continue
        table.append(root, CARRIED_RECORD, sch.CARRIED, {
            "id": ident, "component": f.package, "version": f.version, "severity": f.severity,
            "reason_no_fix": "standing alarm: triage pending" if f.fixed else "no upstream fix at detection",
            "owner": owner, "milestone": "triage", "milestone_date": (today + datetime.timedelta(days=days)).isoformat(),
            "review_by": (today + datetime.timedelta(days=days)).isoformat(), "status": "detected",
            "status_history": f"{today.isoformat()}:detected", "side": cfg.side if cfg else sch.UNKNOWN})
        item_id = "ALARM-" + ident.replace("/", "-").replace("@", "-")
        if not (pathlib.Path(root) / lifecycle.ITEMS_DIR / f"{item_id}.md").exists():
            lifecycle.create_item(root, item_id, "standing-alarm",
                                  f"Finding {ident} is fixed, carried with proof, or accepted with a recorded reason, within {days} days of {today.isoformat()}.")
        raised.append(ident)
    return raised


def resolve(root, cfg, ident, status, note=""):
    """Append a row moving an alarm finding to a new status; history is appended, never rewritten."""
    if status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}")
    latest = latest_rows(root)
    if ident not in latest:
        raise ValueError(f"no alarm or carried finding {ident}")
    r = dict(latest[ident])
    today = datetime.date.today().isoformat()
    values = {c: r[c] for c in sch.CARRIED[2]}
    values["status"] = status
    values["status_history"] = f"{r['status_history']}; {today}:{status}" + (f" ({note})" if note else "")
    values["side"] = cfg.side if cfg else sch.UNKNOWN
    table.append(root, CARRIED_RECORD, sch.CARRIED, values)
    return values


def intervals(root):
    """(id, detected date, resolved date or None, days) for every alarm/carried finding."""
    out = []
    for ident, r in latest_rows(root).items():
        hist = [h.strip() for h in r["status_history"].split(";") if h.strip()]
        first = hist[0].split(":")[0]
        last = hist[-1]
        resolved = last.split(":")[0] if any(last.split(":", 1)[1].startswith(s) for s in ("fixed", "accepted")) else None
        try:
            d0 = datetime.date.fromisoformat(first)
            d1 = datetime.date.fromisoformat(resolved) if resolved else datetime.date.today()
            out.append((ident, first, resolved, (d1 - d0).days))
        except ValueError:
            out.append((ident, first, resolved, None))
    return out
