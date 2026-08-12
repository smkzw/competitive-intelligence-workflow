Active task: .trellis/tasks/08-12-phase-3-evidence-gates-recovery

You are Cursor CLI continuing the same finite-code execution-manager session for `ci_phase3_task31_implementation`. Read the current project `AGENTS.md`. This is a read-only integration review after worker_02 closed the final two Luna P0 findings. You may veto or recommend a bounded repair; you do not own final acceptance.

Hard boundaries:

- Work only inside `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`.
- Do not modify source, tests, policies, schemas, Trellis state, acceptance records, or prior runner reports.
- Do not perform security testing. Review functional evidence integrity and supported API behavior only.
- Runner-managed output path: `runs/execution/ci_phase3_task31_implementation/manager_followup_04.md`. Do not write it through tools.
- Preserve the documented P2 boundary: context-free `ReportGateResult` membership requires a future GateSpec-bearing loader. Do not relabel it P0/P1 unless you find a current authoritative load path.

Read these files only:

- `runs/codex-subagent_ci_phase3_task31_acceptance_followup3.md`
- `context/ci_phase3_task31_pause_2026-08-12.md`
- `runs/execution/ci_phase3_task31_implementation/worker_02_followup_05.md`
- `.trellis/tasks/08-12-phase-3-evidence-gates-recovery/implement.md`
- `docs/decisions/0011-phase-3-evidence-gates-and-recovery.md`
- `src/ci_workflow/gates/models.py`
- `src/ci_workflow/gates/evaluator.py`
- `src/ci_workflow/gates/coverage.py`
- `src/ci_workflow/gates/__init__.py`
- `tests/unit/test_gate_evaluator.py`
- `tests/reports/test_report_specific_gates.py`
- `tests/reports/test_gate_override_strictness.py`

Review goals:

1. Reproduce or inspect the exact two regressions:
   - `test_aggregate_rejects_model_copy_tampered_batch_key_or_unit_results`
   - `test_public_batch_constructor_rejects_detached_unit_results_from_changed_snapshot_or_spec`
2. Verify the authoritative supported path is atomic `evaluate_report(spec, snapshot, bindings, contract_version=...)`; neither package-root exports nor production call sites offer a supported detached `unit_results` constructor/aggregate pair.
3. Verify internal aggregation explicitly revalidates current batch content/key before semantic aggregation, including Pydantic `model_copy` bypass.
4. Verify raised thresholds and object-identical new snapshots force real reevaluation, while `recompute_report_result` remains compatible and parent results immutable.
5. Search for all current production/test call sites; do not accept a rename-only repair if another supported route still permits re-stamping.
6. Confirm prior Task 3.1 invariants remain represented by the exact three-file suite and no tests were weakened to avoid failure.

Codex independently observed after the worker:

- two new attacks: 2 passed;
- Task 3.1 trio: 143 passed;
- full suite: 331 passed;
- Ruff, strict mypy, package verify, public API probe, and diff check passed.

Return a compact manager handoff with sources read, searches/tests run, pass/fail by goal, any failed paths or uncertainty, exact P0/P1/P2 count, and a verdict line `PASS; P0=0; P1=0` or `FAIL; ...`. Do not write acceptance/Trellis records and do not claim Task 3.1 completed.
