# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Scanner image pins (spec 01 REQ-4.3.1–4.3.3). Every scanner reference carries
a tag or digest; the scanner whose detection data is embedded in the image is
pinned to a moving tag — a digest or an immutable patch tag is rejected."""
from ..outcome import Outcome
from ..scan import images

NAME = "scanner-pins"


def run(root, cfg):
    if not images.SCANNERS:
        return Outcome.could_not_run(NAME, "no scanner images are defined")
    probs = images.pin_problems()
    if probs:
        return Outcome.found(NAME, f"{len(probs)} scanner reference(s) violate the pin rule", probs, blocking=True)
    embedded = [c for c, (_, _, e) in images.SCANNERS.items() if e]
    return Outcome.clean(NAME, f"{len(images.SCANNERS)} scanner images pinned; {len(embedded)} with embedded data on a moving tag")
