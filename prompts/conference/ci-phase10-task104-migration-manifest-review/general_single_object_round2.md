This is targeted continuation round 2 in the same session. Do not restart or open a new session.

Codex implemented the blockers from your first review. Reopen the current files and verify the repairs independently:

1. `tests/migration/test_manifest_closure.py` now fixes exact UTF-8 sentinel marker text per sensitive category and asserts each `source_sha256` equals the computed marker digest.
2. `docs/acceptance/migration.md` now publishes the marker text and hash recipe, and explains that no credential content is included.
3. Sensitive session/cache records now use SHA-256 `f8af859b...b0af8`, computed from `legacy-sensitive-session-and-cache-content-not-read-v1`; credentials retain the independently documented credential marker.
4. The two broken spec anchors were changed to `#203-切换门槛` and `#204-删除旧工程`.
5. `kangzhe-core-design-contract` now cites ADR 0002 §11 as the live-source observation, while the acceptance document distinguishes Task 10.4 current old-path observation from the project-internalization snapshot in `contracts/kangzhe/manifest.json`.
6. Codex reran the migration suite: 12 passed; Ruff passed; `LEGACY_REF_OK` passed.

Confirm whether your prior D1 P1, D2/D3 P2 findings are closed. Recheck the 10-item migrated whitelist, 11 required exclusion categories, D01-D70 archive, sensitive no-content boundary, and Task 10.5/10.8 separation. Return a complete updated review with explicit P0/P1/P2 counts and an unconditional accept/reject recommendation under the rule P0=0 and P1=0. Do not request unrelated scope expansion.
