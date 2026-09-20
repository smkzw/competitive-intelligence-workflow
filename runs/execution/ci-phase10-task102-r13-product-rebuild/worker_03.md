# Execution Output: ci-phase10-task102-r13-product-rebuild - worker_03

## Boundary And Context Check

- Scope limited to C report HTML, C renderer, C templates/assets, and C acceptance coverage.
- No PDF, PPT, security, clinical, regulatory, or runner-report work performed.
- No runner-managed report paths written.
- Browser checks were functional smoke checks only, not final visual or clinical/regulatory acceptance.

## Work Performed

- Replaced the previous four-field C overview/design-map crop with a complete observed-field matrix.
- Added horizontal research × design-element matrix rendering:
  - Trial columns retain product, registry ID, phase, status, region, and role.
  - Rows grouped into nine Chinese design domains.
  - Fixture projection covers 12 observed fields and all 48 observations.
  - Matrix row IDs close exactly over the 48 source observations.
- Added matrix cell evidence drilldown:
  - Full original source text.
  - Scale, threshold, timepoint.
  - Group and analysis-cohort labels.
  - Registry field name/definition.
  - Source version and locator.
- Added matrix field-family collapse controls.
- Added multi-select filters for product, trial, design domain, element, scale, and timepoint.
- Synced filters across chart, matrix, table, URL state, and reload restoration.
- Added sticky field column/header and an isolated horizontal matrix scroll container.
- Removed obsolete `coreDesignRows` and `compactFact` placeholder compression paths.
- Added acceptance coverage for full matrix field closure, trial headers, evidence links, filter dimensions, and retired compression paths.

## Artifacts And Evidence

Changed files:

- `src/ci_workflow/renderers/portal/report_c.py`
- `src/ci_workflow/renderers/portal/templates/c/page.html.j2`
- `src/ci_workflow/renderers/portal/templates/c/trial_detail.html.j2`
- `src/ci_workflow/renderers/portal/assets/report-c.js`
- `src/ci_workflow/renderers/portal/assets/report-c.css`
- `tests/acceptance/test_report_c.py`

Functional browser smoke on a clean C-rendered site:

- Matrix count: `1`
- Observed field rows: `12`
- Trial headers: `4`
- Design groups: `9`
- Matrix wrapper overflow: `auto`
- Scale filter options: `3`
- Timepoint filter options: `13`
- First matrix trigger opened the evidence drawer via keyboard `Enter`.
- Drawer exposed source text and cohort wording.
- URL focus state became `?focus=c-nct02260986-population`.
- `Escape` hid the drawer and restored trigger focus.
- Selecting `field_family_zh=人群与标准` reduced visible field rows from `12` to `3`.
- Reload preserved the selected filter and visible row count.
- Document width equaled viewport width at 1024, 1280, 1440, and 1920 px; matrix overflow remained inside its own wrapper.

## Commands And Observations

- `python3 -m py_compile src/ci_workflow/renderers/portal/report_c.py tests/acceptance/test_report_c.py`
  - Passed.
- `node --check src/ci_workflow/renderers/portal/assets/report-c.js`
  - Passed.
- Jinja parsing for `page.html.j2` and `trial_detail.html.j2`
  - Passed.
- `uv run pytest tests/acceptance/test_report_c.py -q`
  - `8 passed`.
- `uv run pytest tests/acceptance/test_report_c.py::test_c_overview_exposes_full_research_design_matrix_and_detail_links -q`
  - `1 passed`.
- `uv run pytest tests/browser/test_r13_product_acceptance.py -k 'r13_c_' -q`
  - Blocked during shared fixture setup before C rendering; see below.

## Blockers Or Missing Environment

- The R13 C browser test module currently constructs A and B sites before C. A-site setup fails in the unrelated `report_a.py` path:
  - `templates/a/regulatory.html.j2`
  - `UndefinedError: 'regulatory' is undefined`
- No C source changes are required for this failure. The targeted C browser assertions were exercised successfully against a clean C site with the browser smoke above.

## Rerun Requests Or Next Step

- Restore or fix the unrelated A renderer fixture context, then rerun:
  - `uv run pytest tests/browser/test_r13_product_acceptance.py -k 'r13_c_' -q`
- Codex owner should perform final visual, clinical, and regulatory acceptance separately.
