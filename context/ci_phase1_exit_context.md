# Task Context: ci_phase1_exit

Created: 2026-08-11 21:51:58
Objective: 执行 Phase 1 确定性退出、真实可移动项目锚点与独立验收
Task type: `finite_code_task`
Risk: `medium`
Selected agent route: `cms-smk` / `deepseek-v4-flash` / `max`

## Trigger Reason

This task was initialized through the Codex x Hermes complex-task entrypoint because it is expected to involve more than three execution steps, research/writing/report/code/report-visual work, or source-grounded verification.

## Source Of Truth

- `.trellis/tasks/08-11-phase-1-project-truth-base/{prd.md,design.md,implement.md}`
- `docs/decisions/0004-phase-1-contract-boundaries.md`
- `docs/specs/competitive-intelligence-workflow-design-v1.2.md` §3、§7–10
- `docs/acceptance/runs/task-1.1/` through `task-1.6/`
- `docs/acceptance/runs/phase-1-exit/regression.txt`
- `docs/acceptance/runs/phase-1-exit/anchors/runtime.json`
- Current source, schemas, migrations and tests named by the Phase 1 deterministic command.

## Scope

- In scope: read-only independent verification of the current Phase 1 implementation, the exact deterministic suite, real moved-project anchor, SQLite lineage/integrity, evidence/event/snapshot/manifest chain and selective capability preflight.
- In scope: identify P0/P1 false-green gaps that would invalidate Phase 1 acceptance.
- Out of scope: edits, Phase 2 source-route implementation, clinical conclusions, A/B/C scientific analysis, full report rendering and delivery-format acceptance.

## Success Criteria

- Exact Phase 1 suite is green and covers the approved Task 1.1–1.6 boundaries.
- Real A/B/C×four-format project can be created, moved, renamed and verified without persisted machine absolute paths.
- SQLite reports `integrity_check=ok`, migration version 8, and rejects orphan project-scoped gate/snapshot/correction records.
- Source dates, complete receipt/gap, event/checkpoint replay, immutable snapshots and current-context-bound artifact manifest have real anchors.
- Real preflight checks only applicable capabilities and all 12 selected deliveries are ready on this host.
- Reviewer returns PASS with P0=0 and P1=0, or provides exact reproducible blockers.

## Risk Boundaries

- Read-only review. Do not edit source, tests, acceptance files, Trellis files, context, metrics or review records.
- Temporary verification files may be created only outside the repository and must be removed or moved to Trash.
- The delegated agent is not final authority; Codex owns verification and acceptance.

## Timeout Policy

- Do not mark the delegated agent failed for slow response alone.
- For complex or artifact-heavy work, wait and poll generously; use conference mode when multiple independent model perspectives are needed.
- Failure requires terminal error, provider exhaustion/rate limit after controlled retry, empty/truncated retry output, or no progress after hard wait plus one retry.
- A provider catalog/auth/transport preflight is diagnostic, not a live capability verdict: timeout, auth refresh failure, or malformed probe output must be recorded and followed by one real route attempt. Only a missing executable or explicit invalid/retired/unlisted model may stop before that attempt.

## Loop Log

- 2026-08-11 21:51:58: Task initialized by `tools/hermes_workflow_guard.py init-task`.
- 2026-08-11 21:52: deterministic Phase 1 suite passed 62 tests; full repository passed 133 tests.
- 2026-08-11 21:54: public CLI project create/preflight/move/verify anchor passed; temporary project moved to Trash.
- 2026-08-11 21:55: evidence/event/checkpoint/snapshot/manifest portability anchor passed and temporary project was removed.
- 2026-08-11 22:14: independent reviewer returned PASS with P0=0 and P1=0 after reproducing 62 exact and 133 full tests.
- 2026-08-11 22:16: audit command was persisted; narrow follow-up passed, but the night route caused `resume_session_reset=true`, so it is not represented as a same-session continuation.
- 2026-08-11 22:18: raw runner streams, temporary prompts and health log moved recoverably to `/Users/smkzw/.Trash/ci-workflow-phase1-exit-20260811-cleanup`; compact reports and acceptance evidence retained.
