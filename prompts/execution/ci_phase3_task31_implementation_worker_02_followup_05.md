Active task: .trellis/tasks/08-12-phase-3-evidence-gates-recovery

You are continuing the same Pi worker_02 session for Task `ci_phase3_task31_implementation`. Read and comply with the current project `AGENTS.md`; preserve every verified change and do not restart the task. This is a bounded repair of the two final P0 findings from the independent Luna acceptance. It is implementation work, not final acceptance.

Hard boundaries:

- Work only in `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`.
- You may modify only:
  - `src/ci_workflow/gates/models.py`
  - `src/ci_workflow/gates/evaluator.py`
  - `src/ci_workflow/gates/__init__.py`
  - `tests/unit/test_gate_evaluator.py`
- Do not modify policies, schemas, coverage, report-specific/override tests, Trellis files, task records, runner reports, or accepted Phase 2 code.
- Runner-managed output path: `runs/execution/ci_phase3_task31_implementation/worker_02_followup_05.md`. Do not write that file through tools.
- Do not add dependencies or security-oriented work. This repair is functional integrity: report evidence from one rule/snapshot must not be accepted as another.

Read these files only:

- `runs/codex-subagent_ci_phase3_task31_acceptance_followup3.md`
- `context/ci_phase3_task31_pause_2026-08-12.md`
- `.trellis/tasks/08-12-phase-3-evidence-gates-recovery/implement.md`
- `docs/decisions/0011-phase-3-evidence-gates-and-recovery.md`
- `src/ci_workflow/gates/models.py`
- `src/ci_workflow/gates/evaluator.py`
- `src/ci_workflow/gates/__init__.py`
- `tests/unit/test_gate_evaluator.py`
- `src/ci_workflow/gates/coverage.py`

Close both P0s with exact mechanical regressions:

1. Add `test_aggregate_rejects_model_copy_tampered_batch_key_or_unit_results`.
   - A valid canonical evaluation must pass.
   - `model_copy(update={"batch_key": ...})` and a nested `model_copy` that alters unit-result fact lineage/count/content must be rejected before report aggregation.
   - Do not rely on `frozen=True` or on initial Pydantic construction. Any authoritative aggregation boundary that receives a model instance must explicitly revalidate its full serialized content and derived digest/key.

2. Add `test_public_batch_constructor_rejects_detached_unit_results_from_changed_snapshot_or_spec`.
   - Results produced for snapshot/spec A must not be accepted or re-stamped under object-identical snapshot B.
   - Results produced under a lower threshold must not pass after a same-version spec content change raises that threshold.
   - The supported public API must make evaluation of units, binding of spec/snapshot identity, and aggregation one evaluator-owned atomic path. It must not expose a supported constructor/aggregate pair that accepts detached `unit_results` and gives them a new identity.
   - If the detached batch/aggregate API is not required by any production consumer, make it private/internal and remove package-root exports. Update tests to distinguish the supported public contract from internal test hooks. Renaming alone is insufficient: the canonical public path must recompute from `spec + snapshot + bindings`, and the internal aggregation path must still reject tampered batch instances.
   - Preserve `evaluate_report(...)` and `recompute_report_result(...)` behavior and signatures.

Preserve all prior Task 3.1 invariants: complete spec-by-universe matrix, threshold enforcement, immutable fact lineage, snapshot/spec fingerprint binding, Chinese medical user notes, A/B/C report behavior, and the documented context-free `ReportGateResult` P2 boundary. Do not relax validation or rewrite tests to avoid the attacks.

TDD and verification:

- First add the two exact tests and demonstrate meaningful RED against the current tree.
- Implement the smallest coherent API-boundary repair.
- Run with project-local temporary directory and no pytest cache:
  - exact two new tests;
  - `tests/unit/test_gate_evaluator.py`;
  - the Task 3.1 three-file suite;
  - full `pytest`;
  - Ruff on changed Python/tests;
  - strict mypy on `src/ci_workflow/gates`;
  - `ci-workflow package verify --root .`;
  - `git diff --check`.

Return a compact handoff containing files read/changed, RED evidence, implementation boundary, command results, any failed paths, uncertainty, session/provider/model recorded by the runner, and the next recommended action. Do not claim acceptance.
