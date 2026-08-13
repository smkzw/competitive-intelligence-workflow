You are continuing the same Pi execution session for Phase 4 Task 4.1. Do not restart the task, redesign the architecture, or create a new execution lane. Work only on the four independently verified P1 functional false-greens below. Keep tools enabled and modify only the Task 4.1 implementation/tests/package data needed for these repairs.

Hard boundaries:

- Work only inside `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`.
- Preserve all unrelated user and prior-task changes.
- Do not commit; parent Codex owns commits and final acceptance.
- Do not implement portal HTML, browser UI, renderer, PDF, HTML-PPT, or PPTX work.
- Do not perform security testing.
- Runner-managed output path: `runs/pi_ci_phase4_task41_review_repairs.md`. Do not write it with tools; return the complete handoff for the runner.

Read these files only:

- `AGENTS.md`
- `.trellis/tasks/08-13-phase-4-common-report-portal/prd.md`
- `docs/specs/competitive-intelligence-workflow-design-v1.2.md`
- `package-manifest.json`
- `schemas/coverage-set.schema.json`
- `schemas/coverage-projection.schema.json`
- `src/ci_workflow/schemas/coverage-set.schema.json`
- `src/ci_workflow/schemas/coverage-projection.schema.json`
- `src/ci_workflow/reports/common/`
- `tests/unit/reports/`
- `tests/contract/test_coverage_set.py`
- `tests/contract/test_page_catalogs.py`
- `tests/contract/test_package_manifest.py`

Task:

Repair these four independently reproduced P1 defects with RED then GREEN exact tests:

1. `validate_report_row_payload` currently accepts a row whose `page_responsibility_id` is not in the frozen report registry. A public standalone row validator must not bypass the registry. Either require report context and mandatory frozen-registry validation, or make raw standalone validation private/internal and expose only a fail-closed public API. Add a direct exact regression test.
2. `PageRegistry.load(root=...)` publicly accepts a caller-selected catalog root. Remove arbitrary-root selection from the public production API. If tests need alternate catalogs, expose only a clearly private test helper that ordinary production validation does not call and that is not exported from `common.__init__`. Add an exact API/signature and injection regression test.
3. `FilteredRowSet.row_set_digest` hashes only row IDs. It must deterministically hash the complete canonical row models sorted by row ID, so changing label, disclosure state, page, snapshot, or any other canonical row content changes the digest. Chart and table must still be equal model-for-model. Add parameterized exact regression tests.
4. Coverage projection validation accepts an arbitrary recomputed `exception_id`. Enforce `exception_id == derive_coverage_exception_id(...)` for every exception before projection identity/digest acceptance, and ensure projection identity is bound to the validated exception identity. Add an exact tamper regression test.

Do not merely change existing assertions to fit behavior. First run each new exact node and retain the RED outcome in the handoff, then implement and rerun the same node GREEN. Afterward run:

- all `tests/unit/reports/`
- `tests/contract/test_coverage_set.py`
- `tests/contract/test_page_catalogs.py`
- relevant package tests
- Ruff on changed Python/tests
- Mypy strict on changed production Python
- full `uv run pytest -q`

Inspect unexpected failures and explain root cause; do not blindly adjust fixtures. Return changed files, RED/GREEN evidence, commands, results, remaining uncertainty, and a concise statement that no commit was made.
