Active task: .trellis/tasks/08-12-phase-3-evidence-gates-recovery

You are Pi (Oh My Pi) continuing the existing finite-code worker session as the implementation worker for Task 3.2. Read the current project `AGENTS.md` and the active Trellis task. Task 3.1 is accepted and immutable input; implement only Task 3.2: double exhaustion, native-Chinese evidence-insufficiency audit packages, and complete no-draft/no-downstream assertions. This is implementation, not final acceptance.

Hard boundaries:

- Work only inside `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`.
- Do not modify accepted Phase 0–2 source/migrations or Task 3.1 gate semantics, policies, schemas, or tests.
- You may create/modify only:
  - `src/ci_workflow/gates/exhaustion.py`
  - `src/ci_workflow/gates/blocker_audit.py`
  - `src/ci_workflow/gates/__init__.py` only if a supported Task 3.2 public type/function must be exported
  - `schemas/blocker-audit.schema.json`
  - `tests/integration/test_double_exhaustion.py`
  - `tests/integration/test_no_draft_when_blocked.py`
  - `tests/integration/test_no_draft_on_unresolved_key_conflict.py`
  - `tests/integration/test_no_draft_after_scientific_qc_rejection.py`
  - `package-manifest.json` and `tests/contract/test_package_manifest.py` only to register the new schema/module surface
- Do not edit Trellis/task/decision/acceptance/review/metric files or runner reports.
- Do not install dependencies, implement Task 3.3+, build reports, or perform security testing.
- Runner-managed output path: `runs/execution/ci_phase3_task32_implementation/worker_01.md`. Do not write it through tools.

Read these files only:

- `.trellis/tasks/08-12-phase-3-evidence-gates-recovery/prd.md`
- `.trellis/tasks/08-12-phase-3-evidence-gates-recovery/design.md`
- `.trellis/tasks/08-12-phase-3-evidence-gates-recovery/implement.md`
- `docs/specs/competitive-intelligence-workflow-design-v1.2.md`
- `docs/decisions/0011-phase-3-evidence-gates-and-recovery.md`
- `docs/acceptance/runs/task-3.1/verdict.md`
- `src/ci_workflow/domain/evidence.py`
- `src/ci_workflow/domain/enums.py`
- `src/ci_workflow/sources/receipts.py`
- `src/ci_workflow/sources/retries.py`
- `src/ci_workflow/gates/models.py`
- `src/ci_workflow/gates/evaluator.py`
- `src/ci_workflow/gates/__init__.py`
- `src/ci_workflow/storage/paths.py`
- `src/ci_workflow/storage/sqlite.py`
- `src/ci_workflow/storage/migrations.py`
- `migrations/0003_gates_snapshots.sql`
- `migrations/0004_delivery_workflow.sql`
- `schemas/evidence-gap.schema.json`
- `schemas/source-receipt.schema.json`
- `package-manifest.json`
- `tests/contract/test_package_manifest.py`
- `tests/contract/test_evidence_audit_contracts.py`
- `tests/integration/test_route_recovery.py`
- `tests/integration/test_sqlite_migrations.py`
- `tests/unit/test_gate_evaluator.py`
- `tests/reports/test_report_specific_gates.py`
- `tests/reports/test_gate_override_strictness.py`

Required contract:

1. Double exhaustion must be a typed, versioned, fail-closed contract. The search/recovery executor and the independent omission reviewer are separate roles with separate identifiers, inputs, conclusions, and digests. Every blocking gap must bind completed/not-applicable/access-blocked route evidence and the accepted Phase 2 `RecoveryExhaustionProof`; two distinct saturated recovery rounds with no gate-relevant information gain are required. A sentence such as “no material omission” without per-gap review must fail.
2. Keep scientific absence separate from technical failure. Unresolved network/rate-limit/captcha/permission/parser/tool/truncation failures cannot become `not_reported` or `not_publicly_disclosed`; they require completed same-path retries, alternative strategies, and an independent technical diagnosis before an access-blocked conclusion can participate.
3. A blocked report may create only `blockers/<A|B|C>/<version>/audit.json` and `audit.md`. The JSON must validate against the new schema and include the v1.2 minimum fields: report/contract/rule/snapshot identity, failed GateSpec units and objects/fields, current fact/missing/conflict state, impacted products/trials, every applicable route and receipt summary, two information-gain rounds, independent omission-review result, technical diagnosis, residual uncertainty, whether user help is needed, minimal user action, source/attachment links, one delivery directory, and resume node.
4. `audit.md` is native Chinese for a senior clinical-trial medical professional who is visually sensitive and not technically sophisticated. It must say clearly: what product/trial/field blocks the report, what was already tried, whether the reason is genuinely not public/not found after exhaustion or an unresolved technical access issue, whether the user needs to help, the one smallest action, the original link(s), and the one folder. Do not expose prompts, logs, enum values, English headings, “xx门”, “xx信号”, backend status names, or debugging language.
5. Before and after writing a blocker package, mechanically assert the current report/version has no locked report snapshot, coverage set/projection, format job, render queue row, artifact record, or `reports/<report>/<version>/` directory. Do not create a draft, placeholder, empty portal, snapshot row, projection, job, queue item, or artifact record. The blocker directory is not a report directory.
6. Empty/no-eligible cases are typed and distinct: A no eligible innovative product; B no eligible result trial meeting the report minimum; C no eligible trial meeting the core design minimum. A with only preclinical projects and C with one eligible core trial must not be automatically treated as empty failures.
7. Parameterize every applicable critical GateSpec unit from `A-v1.yaml`, `B-v1.yaml`, and `C-v1.yaml`: for each unit, create a non-empty product/trial candidate that is otherwise sufficient and only that unit is blocked. Do not satisfy the plan with empty input only. The test must mechanically assert the enumerated case count equals the critical-unit count derived independently from the three YAML files.
8. Parameterize A/B/C unresolved key-conflict cases and reuse the complete database/queue/artifact/filesystem no-draft assertion. A conflict is not numeric zero and not “未公开”.
9. Parameterize A/B/C cases where GateSpec passed but independent scientific QC rejected the candidate: recoverable rejection returns the typed next state `recovering`; only an exhausted rejection returns `evidence_blocked`. Both reuse all no-draft assertions. Task 3.2 may define the minimal typed read-only QC rejection input needed by these tests; do not implement the later Task 3.7 QC service.
10. All Pydantic models are closed/frozen, digests deterministic, persisted paths relative and version segments validated. Writes must be atomic and idempotent for identical content; a second write with drift under the same audit identity fails rather than overwriting accepted audit history.

TDD and verification:

- First add exactly one meaningful initial RED node to each of the four test files and show `4 failed` for missing Task 3.2 behavior (not import/path/fixture errors).
- Then implement and expand the full parameter matrices.
- Exact GREEN command:
  `.venv/bin/pytest tests/integration/test_double_exhaustion.py tests/integration/test_no_draft_when_blocked.py tests/integration/test_no_draft_on_unresolved_key_conflict.py tests/integration/test_no_draft_after_scientific_qc_rejection.py -q -p no:cacheprovider`
- Report the exact total case count and its decomposition: 3 empty/no-eligible + all critical GateSpec units + 3 conflicts + 3 scientific-QC rejection scenarios.
- Also run Task 3.1 trio, full repository pytest, Ruff on changed Python/tests, strict mypy on `src/ci_workflow/gates`, JSON Schema validation, package verify, and `git diff --check` with project-local bytecode/cache suppression.

Return a compact handoff: files read/changed, RED proof, architecture and user-language choices, exact counts/commands/results, failed paths and diagnoses, uncertainty, provider/model/session recorded by the runner, and next action. Do not claim Task 3.2 acceptance or Phase 3 completion.
