You are Pi executing Phase 4 Task 4.1 in a Codex-controlled workflow.

First fully read `/Users/smkzw/.hermes/SOUL.md`, workspace `AGENTS.md`, and `context/ci_phase4_task41_context.md`. State honestly in the final report whether the full SOUL file was read.

Read these files only:
- `AGENTS.md`
- `context/ci_phase4_task41_context.md`
- `docs/specs/competitive-intelligence-workflow-design-v1.2.md`
- `docs/architecture/page-catalogs/A.yaml`
- `docs/architecture/page-catalogs/B.yaml`
- `docs/architecture/page-catalogs/C.yaml`
- `docs/architecture/filter-contracts/common.yaml`
- `docs/architecture/filter-contracts/A.yaml`
- `docs/architecture/filter-contracts/B.yaml`
- `docs/architecture/filter-contracts/C.yaml`
- `docs/architecture/format-contracts/html.yaml`
- `docs/architecture/format-contracts/pdf.yaml`
- `docs/architecture/format-contracts/html-ppt.yaml`
- `docs/architecture/format-contracts/pptx.yaml`
- `tests/contract/test_page_catalogs.py`
- `tests/contract/test_filter_contracts.py`
- `tests/contract/test_format_contracts.py`
- `package-manifest.json`
- `pyproject.toml`

Write exactly one output file: `runs/pi_ci_phase4_task41.md`. This path is runner-managed: do not use tools to write it; return the report so the runner persists it.

Hard boundaries:
- Work only inside `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`.
- Read the source-of-truth files named in the context, then only directly affected adjacent source/tests/contracts.
- You are authorized to create/edit only Task 4.1 production files: `src/ci_workflow/reports/common/{__init__,coverage,view_state,page_registry,chart_specs}.py`, `schemas/{coverage-set,coverage-projection}.schema.json`, `tests/unit/reports/{__init__,test_view_model}.py`, `tests/contract/test_coverage_set.py`, and the surgical package-manifest entry or package-data copy if required. Do not edit specs, approved plan, Trellis, context, prompts, runs/reviews/metrics, frozen page/filter/format contracts, Phase 3 code/data, renderers or visual assets.
- Do not commit or stage. Runner owns `runs/pi_ci_phase4_task41.md`; return the complete report, do not write it.
- No browser/visual/PPT/PDF, external research, installation, security or unrelated refactor.

Implement RED-first from first principles. The models must support a lazy, visually sensitive Chinese clinical-trial user later, but this task is only the stable data/view contract:

1. Canonical immutable `CoverageSet` bound to project/contract/report/version/data cutoff/evidence snapshot/claim snapshot and deterministic identity/digest. Each coverage item has a stable item ID and closed responsibility kind for chapter/page/product/trial/claim/chart/table/evidence/appendix, plus page responsibility ID and referenced stable identities. Reject duplicate semantic identities, empty refs, unknown responsibility, mixed report/snapshot, and mutable/free-form replacement of required identity.
2. Immutable `CoverageProjection` bound to exactly one coverage set, snapshot and output format. It records covered canonical item IDs and structured versioned exceptions with omitted item, replacement expression, concise Chinese rationale and equivalence evidence. Reject new/unknown items, duplicate coverage/exception, covered+excepted overlap, exception without replacement/evidence, or any unexplained difference. HTML/PDF cannot omit required complete tables; HTML-PPT/PPTX may only use approved chart-equivalence exception consistent with frozen format contracts.
3. Stable `ReportRow`/ReportViewModel identity: row ID is deterministically derived from scientific identity fields (fact/claim/product/trial/group/endpoint/event/timepoint as applicable), not label/order/format. Sorting, filtering, Chinese display label, or format changes preserve IDs; insufficient identity and duplicates fail closed. Bind every row to one locked snapshot and page responsibility.
4. One module gets one immutable filtered row set. A `ChartTableModule` or equivalent derives chart row IDs and full-table row IDs from that one set; callers cannot separately inject chart/table rows. Both sets must be exactly equal, including accurate disclosed-missing states; filtering to empty stays empty and does not widen scope.
5. Page registry loads the frozen A/B/C YAML catalogs rather than duplicating page lists. Preserve Chinese labels and separate static pages from dynamic product/trial detail route responsibilities. Validate route IDs/slugs/templates as identities, reject duplicate routes and unknown report kinds; provide deterministic sitemap expansion from all supplied snapshot products/trials, never Top-N/fixed examples.
6. `chart_specs.py` in this task declares only the minimum chart/table input linkage and stable row-set contract needed by Task 4.1. Do not pre-implement Task 4.4 chart compatibility logic.
7. Schemas independently enforce the representable structure. For semantic/cross-array rules Draft 2020-12 cannot express, production validators must enforce them and tests must state that boundary honestly.

Tests must include positive and adversarial cases for every invariant. Use Chinese-native labels/rationales in fixtures without backend/log wording. Run:
- exact two planned files;
- existing Phase 0 page/filter/format contract tests and Phase 3 snapshot/scientific-QC regression relevant to bindings;
- Ruff, strict mypy, Schema checks, package verify, `git diff --check`, full pytest.

Final report headings exactly:
# Execution Output:
## Boundary And Context Check
## Work Performed
## Artifacts And Evidence
## Commands And Observations
## Blockers Or Missing Environment
## Rerun Requests Or Next Step

Return exact counts and limitations. Do not self-accept.
