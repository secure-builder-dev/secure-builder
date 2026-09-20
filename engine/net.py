# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""The only door to the network (spec 04 REQ-2.2; spec 01 REQ-8.4.1, §14).

Exactly three components may reach the network — the currency checker, scanner
image acquisition, and the remediation-data updater — and only when the mode
permits. Every other component that wants a connection is a defect, and the
self-scan check (engine/checks/no_network.py) finds any module that imports a
socket-level library directly instead of coming through here.

In disconnected mode a fetch attempt without the offline flag is an error,
never a silent fallback (04 REQ-3.4).
"""
import urllib.request

ALLOWED_CALLERS = frozenset({"currency", "scanner-images", "detection-data"})


class NetworkForbidden(Exception):
    pass


def permitted(mode, caller):
    """Return None if the caller may fetch under this mode, else the reason not."""
    if caller not in ALLOWED_CALLERS:
        return (f"component '{caller}' is not permitted to reach the network; "
                f"only {sorted(ALLOWED_CALLERS)} are")
    if mode == "disconnected":
        return f"mode is disconnected: '{caller}' must not attempt a connection (use the offline path)"
    if mode not in ("connected", "local"):
        return f"mode {mode!r} is not a known mode; refusing to infer connectivity"
    return None


def fetch(url, *, mode, caller, timeout=30):
    why = permitted(mode, caller)
    if why:
        raise NetworkForbidden(why)
    with urllib.request.urlopen(url, timeout=timeout) as resp:  # the one live fetch
        return resp.read()
