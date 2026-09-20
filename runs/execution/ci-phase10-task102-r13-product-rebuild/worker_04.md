# Execution Output: ci-phase10-task102-r13-product-rebuild - worker_04

## Boundary And Context Check

- Scope limited to HTML browser and visual acceptance for A/B/C.
- No PDF, PPT, or security work performed.
- No production source files modified.
- Added only the browser acceptance artifact:
  - `tests/browser/test_r13_product_acceptance.py`

## Work Performed

Added Playwright acceptance coverage using Chromium and WebKit:

- Responsive surfaces at `1024/1280/1440/1920`.
- Offline/file URL loading, page geometry, console errors, page errors, and remote-request checks.
- A:
  - Bubble button/ARIA semantics.
  - Tab/Enter/Space-compatible keyboard activation.
  - Product insight drawer, four tabs, summary fields, dossier link.
  - Escape close and focus restoration.
  - Legend activation.
  - `focus=<product-id>` URL restoration.
  - Empty-AESI absence from page, chart, legend, table, and filters.
- B:
  - Synthetic four-product/four-trial EASI-75 cross-trial grouping.
  - Product/trial/arm/timepoint/population/statistical-form identity.
  - Treatment/control series.
  - Complete chart table and chart–table row synchronization.
  - Real PNH baseline semantic columns and trial identity.
- C:
  - Full field-by-trial matrix from all observed real-fixture fields.
  - Sticky first column and local horizontal scrolling.
  - Keyboard evidence drawer opening, source content, URL focus, and focus restoration.
  - Multi-select field-family filter URL state and reload persistence.

## Artifacts And Evidence

Acceptance test:

- `tests/browser/test_r13_product_acceptance.py`

Visual evidence retained:

- `tmp/r13-worker04/a-matrix-1024.png`
- `tmp/r13-worker04/a-matrix-1280.png`
- `tmp/r13-worker04/a-matrix-1440.png`
- `tmp/r13-worker04/a-matrix-1920.png`
- `tmp/r13-worker04/b-efficacy-safety-matrix-1024.png`
- `tmp/r13-worker04/b-efficacy-safety-matrix-1280.png`
- `tmp/r13-worker04/b-efficacy-safety-matrix-1440.png`
- `tmp/r13-worker04/b-efficacy-safety-matrix-1920.png`
- `tmp/r13-worker04/c-design-map-1024.png`
- `tmp/r13-worker04/c-design-map-1280.png`
- `tmp/r13-worker04/c-design-map-1440.png`
- `tmp/r13-worker04/c-design-map-1920.png`

Visual observations:

- A 1024px capture still shows a static bubble visualization without the verified product-drawer interaction.
- B 1024px capture shows the older single-observation matrix surface rather than the required cross-trial efficacy comparison.
- C 1024px capture shows the older “核心设计差异” summary and flat table, not the full field-by-trial matrix.

## Commands And Observations

`uv run ruff check tests/browser/test_r13_product_acceptance.py`

- Passed: `All checks passed!`

`uv run pytest tests/browser/test_r13_product_acceptance.py -q -k r13_b_efficacy`

- Passed: `2 passed, 12 deselected`
- Cross-trial EASI-75 grouping and chart/table identity contract currently pass in Chromium and WebKit.

`uv run pytest tests/browser/test_r13_product_acceptance.py -q -k r13_b_real_baseline`

- Passed: `2 passed, 12 deselected`
- Real PNH baseline semantic columns and trial identity currently pass in both engines.

`uv run pytest tests/browser/test_r13_product_acceptance.py -q -k r13_c_matrix_filter`

- Passed: `2 passed, 12 deselected`
- Field-family filter URL state and reload persistence currently pass in both engines.

`uv run pytest tests/browser/test_r13_product_acceptance.py -q -k r13_c_full`

- Failed: `2 failed, 12 deselected`
- Matrix rendering, all observed fields, sticky column, local scroll, drawer opening, source content, and URL focus passed.
- Failure: after Escape, `document.activeElement` was not restored to the matrix trigger in Chromium or WebKit.

`uv run pytest tests/browser/test_r13_product_acceptance.py -q -k r13_a_empty`

- Failed: `2 failed, 12 deselected`
- Empty-AESI fixture still exposes `特别关注不良事件` in the A safety-page explanatory text.
- The failure occurs before the remaining absence assertions can complete.

`uv run pytest tests/browser/test_r13_product_acceptance.py -q -k r13_a_bubble`

- Setup error in both engines.
- Fresh A site generation fails before browser interaction:
  - `src/ci_workflow/renderers/portal/report_a.py:894`
  - `src/ci_workflow/renderers/portal/templates/a/regulatory.html.j2`
  - `jinja2.exceptions.UndefinedError: 'regulatory' is undefined`

Existing browser suite:

- `11 failed, 423 passed`
- Known failures include packaged `assets/portal/charts.js` differing from the package copy and wheel import failure from undefined `_enum_value`.

## Blockers Or Missing Environment

R13 is not accepted:

1. A site generation is blocked by the missing `regulatory` template context.
2. Empty-AESI safety copy still names the absent category.
3. C evidence drawer does not restore focus after Escape.
4. Existing full browser suite still has packaged-asset and wheel-runtime failures.
5. Candidate source changed between browser runs; the final surface must be rerun after source edits stabilize.

## Rerun Requests Or Next Step

After the production fixes land:

```bash
uv run pytest tests/browser/test_r13_product_acceptance.py -q
uv run pytest tests/browser -q
```

Re-capture the 12 visual screenshots after the final rerun, with explicit manual checks at all four widths.
