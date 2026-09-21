# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""The pre-execution guard (spec 03 §4.2–4.3; spec 01 REQ-3.5.3).

Refuses exactly three commands before they reach the network: a push to the
protected branch, a merge while on the protected branch, and a remote merge.
Nothing else. A hook that blocks broadly gets disabled, and a client-side hook
is defence in depth — it reduces accidents and is not the control; the platform's
branch protection is (spec 04 REQ-5.2).
"""
import re
import shlex


def _words(command):
    try:
        return shlex.split(command, posix=True)
    except ValueError:
        return command.split()


def blocks(command, protected_branch, current_branch):
    """Return the reason the command is refused, or None when it is allowed."""
    w = _words(command)
    if not w:
        return None
    # normalise "git -C path push" and similar leading options
    if w[0] == "git":
        i = 1
        while i < len(w) and w[i].startswith("-") and w[i] not in ("--",):
            i += 2 if w[i] in ("-C", "-c") else 1
        sub = w[i] if i < len(w) else ""
        args = w[i + 1:]
        if sub == "push":
            targets = [a for a in args if not a.startswith("-")]
            refspecs = targets[1:] if len(targets) > 1 else []
            if any(re.fullmatch(rf"(\+?[\w./-]+:)?{re.escape(protected_branch)}", r) for r in refspecs):
                return f"push to protected branch '{protected_branch}'"
            if not refspecs and current_branch == protected_branch:
                return f"push from protected branch '{protected_branch}' (would update it)"
            if "--all" in args or "--mirror" in args:
                return f"push --all/--mirror would update protected branch '{protected_branch}'"
        if sub == "merge" and current_branch == protected_branch:
            return f"merge while on protected branch '{protected_branch}'"
    if w[0] == "gh" and len(w) >= 3 and w[1] == "pr" and w[2] == "merge":
        return "remote merge via the hosting platform"
    if w[0] == "glab" and len(w) >= 3 and w[1] == "mr" and w[2] == "merge":
        return "remote merge via the hosting platform"
    return None
