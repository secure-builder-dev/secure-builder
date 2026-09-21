# Project hooks

© 2026 Casey Houle. All rights reserved.
ENGINE-OWNED: local edits to this file are discarded on update

Pre-execution hooks the harness places in a project. They block exactly the
dangerous commands — push to the protected branch, merge while on it, remote
merge — and nothing else (spec 03 §4). A client-side hook reduces accidents; it
is not a control, and the degradation statement says so.
