Trellis SessionStart was already loaded. I’ll re-verify the prior P1/P2 findings against the current tree only, without reading other reviewer reports.The resume path has been rewritten. I’ll read the new control-flow, tests, and then re-check the prior P1/P2 items against that.Prior P1s are closed in the current tree: resume now rebinds canonical input, records current-run reuse/terminal events, and fail-closes on changed evidence. Remaining issue is a P2 control-graph lag, not a user-facing false green.

# Conference Participant Output: ci_phase3_task36_acceptance - cursor_resume_reverify

**PASS** — P0=0, P1=0, P2=1. Prior P1-1 and P1-2 are closed in the current tree. Codex should still re-run the commands below before accepting; this reviewer did not write the runner-owned file and did not execute pytest in this read-only session.

## Boundary Check

- Same independent Cursor/Grok session `91cbac3e-56b0-4ec7-bd62-08440bac1b71`. No worker/other reviewer reports read. No source edits.
- Read: previously authorized Task 3.6 sources/tests/context/plan, plus current `run_service.py`, `fixture_runner.py`, `cli.py`, and the four exact test files plus `test_cli_command_catalog.py`.
- Packaging: Task 3.6 wheel members vs Task 9.5 full bundle — not counted as 3.6 P1; `parents[3]` data loading is unchanged in kind, not newly worsened.
- Live pytest/CLI/wheel were not re-executed here (read-only session). Verdict is source-verified against the current dirty tree and the tests that now encode the prior probe.

## Independent Work Product

### Prior findings vs current tree

| Prior item | Current status |
|---|---|
| **P1-1** Unchanged-input `--resume` / fresh `RunContext` inherits `evidence_blocked` with empty current evidence, no checkpoint, no blocker binding | **Closed** |
| **P1-2** `resume` unused; CLI cannot bind/retry universe; failed-input CLI resume reports `running` | **Closed** |
| **P2** FX05 missing schema-invalid case | **Closed** |
| **P2** catalog `expected.outcome` not enforced | **Closed** |
| **P2** stale FX02/EX01 docs | **Closed** |
| Bare-wheel schemas/policies/fixtures/migrations | **Not a 3.6 P1** (Task 9.5); loaders still use repo-root `parents[3]`, no new wheel-data regression |

### 1. First no-draft A, then CLI / fresh-context unchanged `--resume`

Production CLI still calls `run_project(root, resume=args.resume)` with no caller `RunContext`. Resume now binds `evidence/library/universe.json` before any node dispatch, hydrates typed evidence, and fail-closes if a terminal blocked report’s gate digest no longer matches.

```793:806:src/ci_workflow/application/run_service.py
    if resume:
        if ctx.universe_input_path is None:
            canonical = project_root / CANONICAL_UNIVERSE_RELATIVE_PATH
            if canonical.is_file():
                ctx.universe_input_path = canonical
        ...
        _check_resume_terminal(all_events, contract, ctx)
```

Without `--resume`, a project that already has events is rejected (Chinese, exit 2 via `ContractConfigError`). Reuse is no longer implicit.

Already-blocked reports are not re-driven; blocker files must still exist:

```1063:1081:src/ci_workflow/application/run_service.py
        if report_states.get(report_object_id) == "evidence_blocked":
            ...
            if not (
                (package_dir / "audit.json").is_file()
                and (package_dir / "audit.md").is_file()
            ):
                raise ContractConfigError(...)
            node_summary[f"decision:{kind_value}"] = "preserved"
            continue
```

`_finalize` refuses `evidence_blocked` with zero current-run events.

**Tests that now are the probe:**
- `tests/integration/test_cli_command_catalog.py::test_cli_project_run_resume_rebinds_canonical_input_and_preserves_blocked_decision` — real `ci-workflow fixture run` (exit 4) then `ci-workflow project run --resume` (exit 4,「证据不足」, not「已启动」); `outputs==[]`; `reused_artifacts` are the two blocker files; current-run `run.node.reused` and `run.terminal_decision.recorded`; no new `graph.node.completed`.
- `tests/integration/test_project_run_cli.py::test_project_run_resume_...` run 3 — `run_project(project_root, resume=True)` with no caller context after a successful block.

### 2. Current-run reuse events, terminal decision, checkpoint, `reused_artifacts`, tamper

On digest-matched reuse, the current run appends `run.node.reused` with `source_run_id` / `source_event_id` / input and completion digests. Unchanged blockers go to `reused_artifacts` (not `outputs`). `_append_terminal_decision_events` records `decision_source=reused`, `gate_input_digest`, and the same artifact tuples. `validate_run_manifest` re-checks reused sha/size/`mtime_ns` and requires a unique current-run terminal event whose `artifacts` match.

EX02 run 3 asserts five reuse events, one terminal event, `checkpoint_id`, `{run_id}--*.json`, then tamper of `audit.md` → `RunError` matching「复用产物」. FX04 extra test now expects `reused_artifacts` instead of a silent empty output list.

### 3. Failed-input then canonical file; changed evidence on terminal block

EX02 run 1 fails on missing `evidence/library/universe.json` (exit 2, checkpoint written). Run 2 is `run_project(..., resume=True)` with **no** caller path; the file is discovered, universe/gate/recovery complete, blockers are new `outputs`. That is the production CLI resume function.

CLI missing-file after a blocked fixture run: delete canonical universe → `--resume` exit 2, stderr contains「证据」, not「已启动」.

Changed typed evidence (`evidence_id` → new digest) on a blocked project: `_check_resume_terminal` raises `ContractConfigError` matching「重新打开」**before** dispatch; event count unchanged.

### 4. Schema-invalid fixture, expected-outcome, stale docs

- FX05 case 8: `created_at` without offset → `FixtureCaseError` via schema format `offset-date-time`.
- `run_fixture_case` compares `run_result.outcome` to `case["expected"]["outcome"]`.
- `test_fixture_run_rejects_outcome_mismatch_against_catalog_expectation` monkeypatches a `running` result for `no-draft-a-empty` and expects「运行结果与预期不符」.
- FX02 module docstring now says catalog/digest/input validation **before** renderer check. EX01 docstring now says `running`, matching the assertion.

### Remaining P2 (not acceptance-blocking)

**P2-1 — project family not moved to `blocked` on fail-then-first-block resume**

`coordinator.reconcile` still runs only if **this** run submitted a project transition. EX02 run 1 already bootstrapped `project → running`; run 2 then evidence-blocks the report but skips reconcile. FX06’s first fixture run still reaches `project → blocked`. User-facing outcome/CLI/blockers/current manifest are honest (`evidence_blocked` / exit 4). Control-graph project state can remain `running` while `report_evidence` is `evidence_blocked`.

- File: `src/ci_workflow/application/run_service.py` (coordinator gate ~1093–1107) vs EX02 run 2.
- Evidence: source; EX02 does not assert a `project`/`blocked` event on run 2.
- Minimal remedy: on `evidence_blocked`, reconcile from persisted project state (or submit the blocked transition) even when bootstrap happened in an earlier run.

### Packaging

No new Task 3.6 wheel-data omission. Keep Task 9.5 as mandatory: installed `ci-workflow fixture run` / `project create` from a bare Python wheel still depend on repo-root schemas/policies/migrations/fixtures.

## Evidence And Assumptions

- Source of truth: current dirty `run_service.py`, `fixture_runner.py`, `cli.py`, EX01–EX02/FX01–FX06 tests, `test_cli_command_catalog.py`.
- Assumption: those tests are intended to be green; this session did not execute them.
- Commands Codex should run:

```bash
uv run pytest tests/integration/test_project_run_cli.py tests/integration/test_fixture_run_cli.py tests/integration/test_fixture_artifact_paths.py tests/integration/test_fixture_case_contracts.py tests/integration/test_cli_command_catalog.py -q --tb=short
```

Focus: `test_project_run_resume_requeues_only_interrupted_or_failed_nodes_and_downstream`, `test_cli_project_run_resume_rebinds_canonical_input_and_preserves_blocked_decision`, `test_fixture_run_rejects_outcome_mismatch_against_catalog_expectation`, FX05 schema-invalid branch.

## Risks, Gaps, And Verification Needs

- Independent live pytest/CLI still required for acceptance; this re-verify is source-level.
- P2-1 is a later reopen/coordinator consistency issue, not a current-run provenance lie.
- `validate_run_manifest` assumes exactly one `run.terminal_decision.recorded` per run (A-only; fine for 3.6).
- `_collect_outputs` now scans only `blockers/` (correct for no-draft A; later renderer tasks must collect `reports/` again).

## Recommended Next Step

Codex should treat prior P1s as repaired, run the commands above, and may accept Task 3.6 if they pass. Do not block 3.6 on the known bare-wheel bundle gap. Optional follow-up (not 3.6 P1): move project family to `blocked` when the first evidence-blocked decision happens on a resume after a failed universe run.
