# Hooks

© 2026 Casey Houle. All rights reserved.

- `pre-commit.py` — governance-set approval, ledger drift, red check, copyright
  header, no assistant attribution. Installed by `python hooks/install.py`.
- `commit-msg.py` — refuses attribution trailers and assistant names in messages.
- `stop-hook.sh` — the inner-loop Stop hook from spec 07 §5.1, for an unattended
  driver. **Not installed by this repository**: it belongs in the operator's own
  assistant configuration outside the repo, and spec 07 §5.3 says to verify by
  hand that it does not fight `drive.sh` before relying on it.
