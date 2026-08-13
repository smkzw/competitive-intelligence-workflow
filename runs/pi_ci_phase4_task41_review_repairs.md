All checks pass. Final handoff:

# Execution Output:

## Boundary And Context Check

- **SOUL read:** per session scope, `AGENTS.md`, `prd.md`, the v1.2 spec (Task 4.1-relevant sections), `package-manifest.json`, both coverage schemas (root + packaged), `src/ci_workflow/reports/common/`, `tests/unit/reports/`, `tests/contract/test_coverage_set.py`, `test_page_catalogs.py`, `test_package_manifest.py` were read. No files outside the Task 4.1 implementation/tests/package-data surface were touched; no frozen catalogs, specs, plan, Trellis, context, prompts, runs, reviews or metrics edited.
- Only 4 P1 repairs done; no architecture redesign, no new execution lane, no portal/renderer/PDF/PPT/security work.
- No commit made — `git log -1` still `1a8a2c2` (Phase 3 acceptance); parent Codex owns commits and final acceptance. `runs/pi_ci_phase4_task41_review_repairs.md` not written by me (returned here for the runner).

## Work Performed

RED-first for each defect (exact nodes added first, run RED, then implemented, same nodes re-run GREEN):

1. **P1 row validator bypassed registry.** `validate_report_row_payload(raw)` accepted any `page_responsibility_id`. Now `validate_report_row_payload(raw, *, report_kind: ReportKind)` requires report context and mandatorily checks the page against `PageRegistry.load()`'s frozen catalog for that report kind (B/C-only or fabricated pages fail; same page passes under its own report and fails under another report). No raw standalone public bypass remains.
2. **P2 arbitrary catalog root.** `PageRegistry.load(root=...)` publicly accepted caller-selected roots. `load()` now takes no arguments (source-tree → packaged layout auto-resolution only); alternate catalogs load exclusively through the private `PageRegistry._load_from_dir(dir)`, which is not exported from `ci_workflow.reports.common` and is not called by any production validator. Tests using tmp catalogs switched to `_load_from_dir`.
3. **P3 digest over row IDs only.** `FilteredRowSet.row_set_digest` hashed only sorted row IDs, so label/disclosure/page/snapshot drift left the digest unchanged. It now hashes the complete canonical row models (`model_dump(mode="json")` of every row, sorted by `row_id`); any canonical content change changes the digest, while chart/table row IDs remain equal and model-for-model canonical (existing single-row-set contract untouched).
4. **P4 arbitrary exception_id.** `check_coverage_projection_semantics` now recomputes `derive_coverage_exception_id(version, omitted_item_id, exception_kind, replacement_expression, equivalence_evidence.row_set_digest)` for every exception and rejects mismatch; `_exception_key` now includes the validated `exception_id`, so projection identity is bound to the validated exception identity (tampering either changes the derived exception id → rejected, or the projection key → projection-id recomputation mismatch).

## Artifacts And Evidence

- Changed production files: `src/ci_workflow/reports/common/view_state.py`, `page_registry.py`, `chart_specs.py`, `coverage.py`.
- Changed tests: `tests/unit/reports/test_view_model.py` (new: `test_standalone_row_validator_requires_frozen_page_in_report_catalog`, `test_load_rejects_caller_selected_root_and_helper_is_private`, parametrized `test_row_set_digest_covers_complete_canonical_row_content` ×5; updated: existing row-validator calls gain `report_kind=`, 3 tmp-path registry tests use `_load_from_dir`, `view()` helper extended with `page=`/`snapshot=`); `tests/contract/test_coverage_set.py` (new: `test_coverage_projection_rejects_tampered_exception_id`; custom-registry test uses `_load_from_dir`).
- No schema/package-data changes needed for these repairs.

## Commands And Observations

- **RED** (4 exact nodes, pre-fix): `8 failed` — P1 (signature TypeError, no registry check), P2 (signature still contained `root`), P3 (all 5 params: identical digest `389a7a06…` across disclosure/label/page/snapshot mutations), P4 (`DID NOT RAISE CoverageBoundaryError`). One test-authoring error surfaced during RED: P4 initially raised `AttributeError: 'FixtureFunctionDefinition' object has no attribute 'items'` — root cause: the new test omitted the `coverage_set` fixture parameter, so `coverage_set` resolved to the pytest fixture function; fixed by adding the parameter (not an implementation defect).
- **GREEN** (same 4 nodes, post-fix): `8 passed in 0.27s`.
- `uv run pytest tests/unit/reports/ tests/contract/test_coverage_set.py tests/contract/test_page_catalogs.py tests/contract/test_package_manifest.py -q` → `69 passed`.
- Ruff on changed Python/tests: one real finding (`E501` line too long in my parametrize list) — wrapped; re-run `All checks passed!`.
- Mypy strict: `uv run mypy src/ci_workflow/reports/ --strict` → `Success: no issues found in 5 source files`.
- `git diff --check` → OK. `ci-workflow package verify --root .` → `PACKAGE_OK version=0.1.0a0 stage=phase-2-accepted`.
- Full `uv run pytest -q` → **535 passed in 58.76s** (527 prior baseline + 8 new cases).

## Blockers Or Missing Environment

- None. No unexpected failures remained unexplained: the only two non-defect failures during the run (P4 fixture-parameter omission, E501 line length) were test-side authoring issues fixed at root, not assertion adjustments.

## Rerun Requests Or Next Step

- No rerun required. Deliverable complete: 8/8 exact repair nodes RED→GREEN, targeted suites 69/69, full suite 535/535, Ruff/mypy/package/diff clean, no commit made.
- Remaining uncertainty (for acceptance): `row_set_digest` determinism rests on Pydantic `model_dump(mode="json")` field-order stability (declaration order) — deterministic by construction, cross-process stable; `validate_report_row_payload` now requires `report_kind` — verified no other callers exist in the codebase. Next step for Codex: re-run the exact nodes and suites in a fresh context, then final acceptance; runner persists this handoff to `runs/pi_ci_phase4_task41_review_repairs.md`.
