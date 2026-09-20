# Checkpoint — R2/R3 browser-contract repair

- **Date**: 2026-09-05
- **Status**: bounded repair accepted; R2, R3 and M2/M3 remain open
- **Goal**: keep the v1.3 HTML-only rebuild moving without inheriting stale 12-page, radar, default-open-table or false `snapshot_locked` assumptions.

## Completed

- Governed science conference `ci-rebaseline-r2-science-review-20260905` completed; Codex verdict remains `Revise` because B/C research-package-to-gate-to-snapshot-to-independent-QC wiring is absent.
- Implemented and verified the first scientific contract corrections: indication cleanup, typed report-scoped QC input, universe closure/recovery receipts, manual-file no-copy validation/rename receipts, and model-assisted semantic adjudication bounded by deterministic hard conflicts.
- Governed browser execution `ci-r2-r3-html-browser-repair-20260905` completed on three isolated copies. Codex selectively merged A/B/C and shared-runtime fixes and accepted that bounded execution.
- Report-data shortcut paths now declare `rendered_unreviewed`; they no longer claim `snapshot_locked`.
- Current portal contract is 11 A pages, 20 B pages and 11 C pages; radar acceptance responsibility removed; complete tables remain collapsed by default.
- Full quality gate passed: Ruff; strict mypy 196 source files; 861 unit/contract tests; legacy runtime-reference scan.
- Focused browser evidence: A 62 passed; B full pass after closing the only two failing cases; C 81 passed; shared chart/drawer/filter/shell 217 passed.
- Codex regenerated a three-report fixture and visually reopened representative A/B/C pages. This is bounded regression evidence, not real-matrix visual acceptance.
- Review gate and execution audit passed. Process outputs were archived.

## Disk hygiene

- Removed three exact isolated APFS work copies (`/tmp/ci-r2-browser-w1.YVyEo7`, `/tmp/ci-r2-browser-w2.uLvZmr`, `/tmp/ci-r2-browser-w3.hfa8tL`), each reporting 5.6 GB logical size before removal.
- Removed the temporary Codex visual fixture/screenshots and regenerated `.pytest_cache`, `.ruff_cache`, `.mypy_cache`, plus source/test/tool bytecode caches.
- Preserved normative files, execution archives, browser runtimes, scientific evidence and protected runtime/session state.

## Open defects / non-acceptance

- B/C do not yet have the A-equivalent typed fresh-source research package, ingestion lineage, report gate, immutable snapshot and independent scientific-QC binding.
- The report-data shortcut is intentionally `rendered_unreviewed`; it cannot be used as scientific or release acceptance.
- Eight indications × A/B/C, all physical pages × four viewports × Chromium/WebKit, three-host fresh install, recovery and RC binding are not complete.
- External earlier real-project manifests have stale package digests and correctly fail closed; verifier weakening is prohibited.

## Next safe action

Create and dispatch a governed R2 execution packet split into: shared typed research-package/lineage primitives, B scientific wiring, and C scientific wiring plus independent integration verification. Merge only after Codex reproduces RED/GREEN evidence in the primary worktree.
