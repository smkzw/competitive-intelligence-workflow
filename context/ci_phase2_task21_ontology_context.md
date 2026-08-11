# Task Context: ci_phase2_task21_ontology

Created: 2026-08-11 22:23:52
Objective: 独立验收 Task 2.1 创新药本体、组合方案和宇宙闭合边界
Task type: `finite_code_task`
Risk: `medium`
Selected agent route: `opencode-go` / `deepseek-v4-flash` / `max`

## Trigger Reason

This task was initialized through the Codex x Hermes complex-task entrypoint because it is expected to involve more than three execution steps, research/writing/report/code/report-visual work, or source-grounded verification.

## Source Of Truth

- `.trellis/tasks/08-11-phase-2-universe-source-truth/{prd.md,design.md,implement.md}`
- `docs/decisions/0006-phase-2-universe-and-source-boundaries.md`
- `policies/ontology/innovation-therapy-v1.yaml`
- `src/ci_workflow/capabilities/ontology_universe.py`
- `tests/unit/test_innovation_eligibility.py`
- `tests/unit/test_regimen_eligibility.py`
- `tests/contract/test_package_manifest.py`
- `docs/acceptance/runs/task-2.1/{red.txt,green.txt}`

## Scope

- In scope: read-only independent verification of Task 2.1 innovation modality inclusion, traditional treatment exclusion, regimen component accounting, boundary review audit and universe-closure behavior.
- In scope: verify policy-driven behavior, stable IDs, package policy/migration registration and exact RED/GREEN evidence.
- Out of scope: edits, Task 2.2 entities, source connectors, live clinical claims, report generation and security testing.

## Success Criteria

- All four approved exact nodes independently pass and fail for the intended reason before implementation.
- ADC and fusion protein are explicit included rules; antihistamine, csDMARD, traditional corticosteroid, generic and biosimilar are explicit exclusions.
- Innovative plus traditional background treatment includes only the innovative component in competitor profiles/counts; pure traditional regimen is excluded.
- Unmatched reformulation, repositioning, fixed combination and unknown items stay review_pending and prevent gate/snapshot/render until an evidence-bound independent decision.
- Reviewer returns PASS with P0=0 and P1=0 or exact reproducible blockers.

## Risk Boundaries

- Read-only. Do not edit source, policy, tests, acceptance records or Trellis files.
- Do not infer innovation from names, marketing wording or free-text similarity.
- The delegated agent is not final authority; Codex owns verification and acceptance.

## Timeout Policy

- Do not mark the delegated agent failed for slow response alone.
- For complex or artifact-heavy work, wait and poll generously; use conference mode when multiple independent model perspectives are needed.
- Failure requires terminal error, provider exhaustion/rate limit after controlled retry, empty/truncated retry output, or no progress after hard wait plus one retry.
- A provider catalog/auth/transport preflight is diagnostic, not a live capability verdict: timeout, auth refresh failure, or malformed probe output must be recorded and followed by one real route attempt. Only a missing executable or explicit invalid/retired/unlisted model may stop before that attempt.

## Loop Log

- 2026-08-11 22:23:52: Task initialized by `tools/hermes_workflow_guard.py init-task`.
- 2026-08-11 22:22: four exact nodes each recorded one expected missing-module failure, then one pass.
- 2026-08-11 22:23: Task suite 4 passed; repository 137 passed; static and package checks passed.
- 2026-08-11 22:31: independent reviewer returned PASS with P0=0 and P1=0 after reproducing RED/GREEN and 137-test regression.
- 2026-08-11 22:32: 4.7 MB raw runner output, temporary prompt and health record moved recoverably to `/Users/smkzw/.Trash/ci-workflow-task21-20260811-cleanup`.
