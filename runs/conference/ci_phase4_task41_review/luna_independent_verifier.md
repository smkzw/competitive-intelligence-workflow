VERDICT: FAIL

P0=0, P1=4, P2=0

Findings:

1. P1 — `validate_report_row_payload` accepts unknown page responsibilities  
   - Location: `src/ci_workflow/reports/common/view_state.py:201-206`
   - Evidence: an in-memory row with `page_responsibility_id="自由页面"` was accepted, while the full view validator rejected it.
   - Impact: public row validation can bypass the frozen A/B/C registry.
   - Repair: require report context and registry validation, or make standalone row validation internal-only.

2. P1 — Public catalog-root override remains exposed  
   - Location: `src/ci_workflow/reports/common/page_registry.py:255-270`; exported in `common/__init__.py:33-39`
   - Evidence: `PageRegistry.load(root=Path.cwd())` was accepted; signature is `(root: Path | None = None)`.
   - Impact: callers can select arbitrary catalog roots through a public API.
   - Repair: remove `root` from public `load`; retain only a private/test loader.

3. P1 — Row-set digest ignores canonical row content  
   - Location: `src/ci_workflow/reports/common/chart_specs.py:66-70`
   - Evidence: changing label, disclosure state, page, or snapshot while keeping the same row ID produced the same `row_set_digest`; both altered rowsets validated.
   - Impact: chart/table and cross-format equivalence can falsely accept changed canonical content.
   - Repair: digest the complete canonical row models, sorted deterministically by row ID.

4. P1 — Coverage projection exception identity is not validated  
   - Location: `src/ci_workflow/reports/common/coverage.py:169-182`, `458-507`
   - Evidence: replacing `exception_id` with an arbitrary value, then recomputing projection ID and digest, was accepted.
   - Impact: immutable coverage exceptions can be altered without rejection.
   - Repair: enforce `exception_id == derive_coverage_exception_id(...)` and bind projection identity to the validated exception identity.

Checks run:

- Exact requested suite: `84 passed, 6 errors`; six errors were `tmp_path` cases blocked before execution by the read-only sandbox having no writable temporary directory.
- Read-only subsets: 25 unit passed; 26 coverage-contract passed; 33 adjacent/package/path tests passed.
- `ci-workflow package verify --root .`: `PACKAGE_OK`.
- Schema and A/B/C catalog byte comparisons: all matched.
- Packaged-source catalog smoke test: A=11, B=21, C=12; dynamic routes preserved supplied IDs.
- Ruff: passed.
- Production registry injection attempts: rejected.

Residual uncertainty:

- Wheel contents and clean isolated installation were not verifiable: the available environment is an editable install, and building a wheel would require writes. Source-level packaged copies passed.
- No files were edited, formatted, committed, repaired, or report-written.
