This is targeted continuation round 2 in the same session. Do not restart broad discovery.

Codex resolved your P2 questions on current files:

1. User authorization now binds `preauthorization_validation_sha256`; Task 10.8 keeps the approved `apply --manifest --authorization --receipt` interface, while optional `--validation-receipt` is only an extra check. Verify that the authorization schema/checks, test helper, apply receipt, docs, and current-state re-observation make this chain coherent without a circular dependency.
2. `credentials=0` was removed. Validate now reports only `escapes=0`, `recovery=passed`, and truthful `content_mode=metadata_only|explicit_content`; the CLI test pins this.
3. Catalog `receipt.owner_status` is explicitly treated as an immutable owner baseline. The verifier now checks status compatibility; exact `owner_task`, frozen digests, and the governed owner-stage release receipt advance closure without mutating case digests. The acceptance note documents this authority boundary.
4. `_safe_receipt_path` now wraps a missing receipts root. The acceptance note documents `--scan-root`, flat `<case_id>.json`, repo-local governance tools, and Task 10.6 recovery-producer dependency.
5. Codex reran the focused tests/Ruff/mypy after these repairs; an expanded final regression will follow your delta verdict.

Read only the current deltas and directly verify whether F1-F3 are closed. Report final P0/P1/P2 counts and any remaining concrete blocker. Return the complete updated Markdown output for your role; Codex remains final authority.
