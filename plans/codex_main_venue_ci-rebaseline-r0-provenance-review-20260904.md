# Codex Main-Venue Plan: ci-rebaseline-r0-provenance-review-20260904

Date: 2026-09-04
Objective: Independently audit R0 provenance recovery, strict quality gate truthfulness, historical source-set demotion, zero-contact legacy-boundary correction, immutable recovery snapshot, and disk-hygiene safeguards; return PASS or VETO with file-and-command evidence, without modifying workspace artifacts.

## Task Decomposition

1. Compare worker_01 claims with the current R0 governance record and exact code.
2. Audit the single quality gate for truthful scope, strict typing and false-green behavior.
3. Audit the historical source-set verifier and negative clean/release semantics.
4. Audit the lexical legacy-reference scanner and synthetic no-resolve test without touching the forbidden target.
5. Audit recovery-snapshot implementation, receipt binding and limitations; separate workspace-verifiable facts from Codex's external physical-state check.
6. Audit milestone disk-hygiene policy for recoverability and destructive-scope safety.
7. Return PASS/VETO with severity, evidence and minimum repairs. Do not edit artifacts.

## Source Packet

- `context/ci-rebaseline-r0-provenance-review-20260904_conference_context.md`
- `docs/governance/r0-provenance-and-quality-gate.md`
- `context/ci-rebaseline-rebuild-20260904_recovery_snapshot_receipt.json`
- `context/ci-rebaseline-rebuild-20260904_prechange_inventory.json`
- `docs/governance/rebaseline-release-source-set-v1.json`
- `docs/governance/rebaseline-release-source-set-v1-postquality.json`
- `tools/gate.sh`
- `tools/check_no_legacy_refs.py`
- `tools/verify_rebaseline_source_set.py`
- `tools/rebaseline_snapshot.py`
- `tests/contract/test_rebaseline_governance.py`
- `tests/contract/test_rebaseline_snapshot.py`
- `tests/migration/test_no_legacy_runtime_dependency.py`
- `runs/execution/ci-rebaseline-rebuild-20260904/worker_01.md`
- canonical v1.3 roadmap/execution constraints relevant to R0.

## Participant Assignments

| Role | Provider | Model | Output |
|---|---|---|---|
| `general_single_object` | `cursor` | `default` | `runs/conference/ci-rebaseline-r0-provenance-review-20260904/general_single_object.md` |

## Conference Panel Coordination

- No sub-venue chair. Codex leads the assigned panel directly.

## Main-Venue Review

- Codex performs the final synthesis and acceptance.
- This conference mode has no Reasonix second-review role.

## Timeout And Retry Tracking

- Start and completion are recorded by the runner log.
- One primary session is dispatched once and awaited to terminal state; any correction request resumes the same session.
- Codex records fallback, late-output and incorporation status in metrics after review.

## Codex Verification Checklist

- Re-run `bash tools/gate.sh` and retain exact scope/count.
- Validate focused R0 tests and `git diff --check`.
- Recompute both external manifest file hashes, check manifest summaries and verify writable-node count is zero without touching the legacy root.
- Ensure participant did not modify files or overclaim external verification.
- Resolve every VETO item before M1 checkpoint; a worker or participant PASS is not final acceptance.
