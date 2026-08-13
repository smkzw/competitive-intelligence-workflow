# Task Context: ci_phase3_task37

Created: 2026-08-13 08:20:42+08:00

## Goal

Implement approved rebuild-plan Task 3.7: a real independent scientific-QC boundary between a deterministic GateSpec pass and a locked report snapshot. Only a current, schema-valid, candidate-bound `accepted` verdict may lock a snapshot. A veto may route to recovery or evidence blocking, but may never create report, coverage, format, render-queue, or artifact records.

## Source Of Truth

- `../.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md`, Task 3.7 SQ01-SQ04 and its exact suite.
- `../.hermes/plans/2026-08-10-competitive-intelligence-multiskill-workflow-design.md`, v1.2 evidence-state and independent-review requirements.
- `.trellis/tasks/08-12-phase-3-evidence-gates-recovery/prd.md` and `task.json`; Task 3.6 is accepted and Task 3.7 is current.
- Current repository contracts: `src/ci_workflow/gates/models.py`, `gates/blocker_audit.py`, `graph/guards.py`, `graph/transitions.py`, `graph/executor.py`, `graph/types.py`, `graph/definitions/new_report.py`, `storage/snapshot_store.py`.
- Existing regression anchor: `tests/integration/test_no_draft_after_scientific_qc_rejection.py` and shared no-downstream assertions in `tests/integration/test_no_draft_when_blocked.py`.
- User corrections retained by the design/plan: no draft below evidence threshold; logs/internal state must not leak into user reports; focus on clinical-research functionality, not system security.

## Scope

- In scope: create `src/ci_workflow/capabilities/scientific_qc.py`, `src/ci_workflow/qc/scientific.py`, and `schemas/scientific-qc-verdict.schema.json`; integrate the Task 3.7 boundary into `graph/definitions/new_report.py`; add the two approved test files and minimal adjacent exports/contracts needed for executable integration.
- In scope: immutable verdict model and deterministic validation; current report/candidate/gate/coverage/source/locator identity binding; freshness and candidate-content drift rejection; input isolation from worker reasoning/scratch/log/prompt material; accept-or-veto only; veto cannot rewrite facts/claims/candidate; real graph transitions and no-downstream assertions.
- In scope: preserve Task 3.2 rejection behavior while converging its public path on the new verdict/decision service where coherent.
- Out of scope: report rendering, browser/visual/PPT/PDF work, clinical content research, network access, host installation, security testing, and unrelated refactoring.

## Success Criteria

- SQ01: GateSpec pass alone never locks. Missing, stale, malformed, wrong-candidate, wrong-report, wrong-gate-result, wrong-coverage, or invalid-source verdicts fail closed. Exactly one current schema-valid accepted verdict allows `scientific_qc -> snapshot_locked`.
- SQ02: verdict binds report kind/version, project/contract, candidate snapshot identity and digest, GateSpec result, coverage identity/digest, source evidence and precise locators, issues, reviewer identity, criteria version, and offset timestamps; semantically empty generic self-review is rejected.
- SQ03: the verifier receives only declared candidate snapshot, acceptance criteria, coverage and evidence/source references. Worker reasoning, scratch notes, prompts, logs, or mutable worker context are absent and rejected if supplied. The reviewer returns a verdict and cannot mutate or rewrite candidate facts/claims.
- SQ04: a schema-valid recoverable veto produces a real accepted transition to `recovering`; an unfixable veto with matching exhaustion evidence produces a real accepted transition to `evidence_blocked`. Both reuse A/B/C no-draft/no-database-row/no-queue/no-artifact assertions.
- Exact suite passes:
  `uv run pytest tests/integration/test_scientific_qc_gate.py tests/graph/test_scientific_qc_isolated_veto.py tests/integration/test_no_draft_after_scientific_qc_rejection.py -q`
- Focused type/lint checks pass; related graph/node/transition and snapshot regressions pass; full suite remains green.
- The implementation is deterministic, test-fixture-driven, and does not fabricate a verdict or accept a plain string such as `accepted`.

## Risk Boundaries

- Work only in this repository. Preserve unrelated user changes.
- Do not modify the approved design or rebuild plan.
- Do not create a report draft or any downstream artifact when QC is missing, invalid, stale, or vetoes.
- Do not weaken existing GateSpec, universe-closure, exhaustion, graph-guard, snapshot-integrity, or no-draft checks to make tests pass.
- The executor may implement and self-test but cannot accept its own work. Codex and an isolated reviewer own acceptance.
- No external/production writes; no browser, rendering, clinical research, or security test.

## Timeout And Recovery

- One declared execution session; allow the runner hard wait up to 120 minutes. No fixed-interval polling and no fallback for latency alone.
- A health/catalog failure is diagnostic; permit one live route attempt. Fallback only after terminal failure/unavailability or unusable output, according to the global route contract.
- If a test exposes a false-green path, investigate the state/data lineage and fix the contract rather than weakening the assertion.

## Loop Log

- 2026-08-13 08:20:42+08:00: Task initialized by workflow guard; current Trellis next task confirmed as 3.7.
- 2026-08-13 08:22:00+08:00: Codex re-anchored from repository state, inspected current node, transition, guard, snapshot, executor, and Task 3.2 no-draft contracts; bounded implementation scope recorded.
- 2026-08-13 08:24:47+08:00: Pi/CMS-SMK connectivity diagnostic timed out after 90 seconds with no stdout/stderr; per global policy this did not preempt the required live attempt.
- 2026-08-13 08:24:47+08:00: After the diagnostic returned, the declared Pi/CMS-SMK live execution attempt continued in runner shell session `83874`; no fallback was selected.
- 2026-08-13 08:30:48+08:00: User requested a lossless pause. Codex sent one normal interrupt to the same runner session. Runner exited 130; no worker report, stdout, source edit, test file, or orphan process existed. Resume from `context/ci_phase3_task37_pause_2026-08-13.md` without creating a replacement task.
- 2026-08-13 resume: Latest global AGENTS digest is `7d76d6202074907f746b25ab2a366c4ea59b7d2ff1e44eddbe2cfeb53cbcd2f5`; finite-code primary remains Pi/CMS-SMK DeepSeek V4 Flash. OMP JSONL proved the original live session is recoverable as `019ff883-4620-7000-8dec-bc07b18315a4`: it is bound to this workspace/model, contains the original Task 3.7 prompt, completed read-only reconnaissance, and stopped at a tool boundary before any source/test edit. Resume this identity instead of starting a new worker.
- 2026-08-13 acceptance: implementation commit `8d50e13`; main exact/contract suite 21 passed, associated gate/graph suite 102 passed, full suite 472 passed, Phase 3 formal exit 277 passed. A real `no-draft-a-empty` run (`run_8f13149186023d423577c8d5`) exited with the defined evidence-blocked code, produced only the Chinese blocker package and internal records, and left report snapshots, coverage sets, artifact records and report/format files absent. The same Luna verifier session concluded `PASS; P0=0; P1=0; P2=1`; P2 is only the external-plan repository pointer note.
