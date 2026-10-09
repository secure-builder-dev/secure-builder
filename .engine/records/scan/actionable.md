# Actionable scan findings

This document exists only while actionable findings exist; its existence blocks the gate.

## Owner: application dependencies

- CVE-2026-2006 [HIGH] postgresql@17.6 (vulnerabilities; fix: 17.8; reported by grype)
- CVE-2026-2005 [HIGH] postgresql@17.6 (vulnerabilities; fix: 17.8; reported by grype)
- CVE-2026-2004 [HIGH] postgresql@17.6 (vulnerabilities; fix: 17.8; reported by grype)
- CVE-2026-2003 [MEDIUM] postgresql@17.6 (vulnerabilities; fix: 17.8; reported by grype)
- CVE-2025-12818 [MEDIUM] postgresql@17.6 (vulnerabilities; fix: 17.7; reported by grype)
- CVE-2025-12817 [LOW] postgresql@17.6 (vulnerabilities; fix: 17.7; reported by grype)

## Owner: infrastructure definitions

- dangerous-subprocess-use-audit [HIGH] scripts/test_all.py (sast; fix: fix the code: Detected subprocess function 'run' without a static string. If this data can be controlled by a malicious actor, it may be an instance of command injection. Aud; reported by semgrep)
- B324-hashlib [HIGH] backend/.venv/Lib/site-packages/httpx/_auth.py (sast; fix: fix the code: Use of weak SHA1 hash for security. Consider usedforsecurity=False; reported by bandit)
- B202-tarfile_unsafe_members [HIGH] backend/.venv/Lib/site-packages/pygments/lexers/_php_builtins.py (sast; fix: fix the code: tarfile.extractall used without any validation. Please check and discard dangerous members.; reported by bandit)
