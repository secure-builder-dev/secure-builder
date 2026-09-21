# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Project configuration — the four axes, the operating mode, the topology.

Spec 01 §2: four project-level values fixed at initialization, stored in one
machine-readable file at a fixed path, read by every component (never passed
as flags). A sentinel means "not yet chosen"; any sentinel makes the gate
return a blocking finding. Forced combinations are applied by the initializer,
never asked.

Spec 04 §1: mode is explicit configuration, never inferred from a failed
connection. Every output that differs by mode states the mode. §10: a project
developed on one network and deployed on another is two instances, not a mode.
"""
import json
import pathlib

from .outcome import Outcome

CONFIG_PATH = ".engine/rules/config.json"          # the fixed, well-known path (REQ-2.1.1)
UNSET = "unset"                              # the not-yet-chosen sentinel (REQ-2.1.3)
SCHEMA = 1

AXES = {
    "track": ("web", "android"),
    "tier": ("IL4", "IL6"),
    "provider": ("aws", "azure", "tactical"),
    "app_type": ("native", "atak"),
}
MODES = ("connected", "local", "disconnected")
TOPOLOGIES = ("single", "low-side", "high-side")

# REQ-2.2.1: combinations that are not independently selectable.
FORCED = {
    ("track", "android"): {"tier": "IL6", "provider": "tactical"},
}
# app_type is Android-only; on the web track it is structurally not applicable.
APP_TYPE_NA = "n/a"


class ConfigError(Exception):
    pass


class Config:
    def __init__(self, data):
        self.data = dict(data)

    # --- axes ---
    @property
    def track(self): return self.data.get("track", UNSET)
    @property
    def tier(self): return self.data.get("tier", UNSET)
    @property
    def provider(self): return self.data.get("provider", UNSET)
    @property
    def app_type(self): return self.data.get("app_type", UNSET)
    @property
    def mode(self): return self.data.get("mode", UNSET)
    @property
    def topology(self): return self.data.get("topology", "single")
    @property
    def side(self): return self.data.get("side", "local")
    @property
    def operators(self): return int(self.data.get("operators", 1))
    @property
    def protected_branch(self): return self.data.get("protected_branch", "main")
    @property
    def timezone(self): return self.data.get("timezone", "UTC")
    @property
    def clock(self): return self.data.get("clock", "workstation clock")
    @property
    def na_threshold(self): return float(self.data.get("not_applicable_threshold", 0.5))

    def get(self, key, default=None):
        return self.data.get(key, default)

    @property
    def shape(self):
        return f"track={self.track} tier={self.tier} provider={self.provider} app_type={self.app_type}"

    def unset_axes(self):
        out = []
        for axis in AXES:
            v = self.data.get(axis, UNSET)
            if axis == "app_type" and v == APP_TYPE_NA and self.track == "web":
                continue
            if v == UNSET:
                out.append(axis)
        if self.data.get("mode", UNSET) == UNSET:
            out.append("mode")
        return out

    def problems(self):
        """Every way this configuration is invalid, in words."""
        out = []
        if self.data.get("schema") != SCHEMA:
            out.append(f"schema is {self.data.get('schema')!r}, expected {SCHEMA}")
        for axis, allowed in AXES.items():
            v = self.data.get(axis, UNSET)
            if v == UNSET:
                continue
            if axis == "app_type" and v == APP_TYPE_NA:
                if self.track != "web":
                    out.append("app_type is n/a but track is not web")
                continue
            if v not in allowed:
                out.append(f"{axis}={v!r} is not one of {allowed}")
        if self.track == "web" and self.app_type not in (APP_TYPE_NA, UNSET):
            out.append("app_type is Android-only; on the web track it must be n/a")
        for (axis, value), forced in FORCED.items():
            if self.data.get(axis) == value:
                for k, want in forced.items():
                    have = self.data.get(k, UNSET)
                    if have != UNSET and have != want:
                        out.append(f"{axis}={value} forces {k}={want}, but {k}={have}")
        mode = self.data.get("mode", UNSET)
        if mode != UNSET and mode not in MODES:
            out.append(f"mode={mode!r} is not one of {MODES}")
        if self.topology not in TOPOLOGIES:
            out.append(f"topology={self.topology!r} is not one of {TOPOLOGIES}")
        if not str(self.side).strip():
            out.append("side identifier is empty")
        return out

    def mode_line(self):
        """Every output that would differ by mode states the mode (04 REQ-1.3)."""
        return f"mode: {self.mode}; topology: {self.topology}; side: {self.side}"


def path_for(root):
    return pathlib.Path(root) / CONFIG_PATH


def load(root):
    """Load the configuration. Raises ConfigError when absent or unparseable."""
    p = path_for(root)
    if not p.is_file():
        raise ConfigError(f"{CONFIG_PATH} not found — project is not initialized")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except ValueError as e:
        raise ConfigError(f"{CONFIG_PATH} is not valid JSON: {e}")
    if not isinstance(data, dict):
        raise ConfigError(f"{CONFIG_PATH} must contain a JSON object")
    return Config(data)


def apply_forced(values):
    """REQ-2.2.1: apply forced combinations rather than asking and validating."""
    out = dict(values)
    for (axis, value), forced in FORCED.items():
        if out.get(axis) == value:
            out.update(forced)
    if out.get("track") == "web":
        out["app_type"] = APP_TYPE_NA
    return out


def init(root, *, track, mode, tier=UNSET, provider=UNSET, app_type=UNSET,
         topology="single", side="local", operators=1, protected_branch="main",
         timezone="UTC", clock="workstation clock"):
    """Write the configuration once. Refuses to overwrite: the file is project-owned."""
    p = path_for(root)
    if p.exists():
        raise ConfigError(f"{CONFIG_PATH} already exists; configuration is fixed at initialization")
    if mode not in MODES:
        raise ConfigError(f"mode must be explicit and one of {MODES}, not {mode!r} (never inferred)")
    values = apply_forced({"track": track, "tier": tier, "provider": provider, "app_type": app_type})
    data = {
        "schema": SCHEMA, **values, "mode": mode, "topology": topology, "side": side,
        "operators": int(operators), "protected_branch": protected_branch,
        "timezone": timezone, "clock": clock, "not_applicable_threshold": 0.5,
        "consistency_blocks": ["verdict-block"],
        "obligation_ceiling": 5, "obligation_max_age_days": 30,        # spec 11 REQ-7.6, 7.7
    }
    cfg = Config(data)
    probs = cfg.problems()
    if probs:
        raise ConfigError("; ".join(probs))
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")
    return cfg


def check(root):
    """The configuration check. Any sentinel is a blocking finding (REQ-2.1.4)."""
    name = "config"
    try:
        cfg = load(root)
    except ConfigError as e:
        if "not found" in str(e):
            return Outcome.found(name, "project is not initialized; no control baseline is defined",
                                    [str(e)], blocking=True)
        return Outcome.could_not_run(name, str(e))
    probs = cfg.problems()
    unset = cfg.unset_axes()
    items = [f"axis '{a}' is not yet chosen" for a in unset] + probs
    if items:
        return Outcome.found(name, f"configuration incomplete or inconsistent ({cfg.shape})",
                                items, blocking=True)
    return Outcome.clean(name, f"{cfg.shape}; {cfg.mode_line()}")
