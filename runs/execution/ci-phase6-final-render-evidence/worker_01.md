# Execution Output: ci-phase6-final-render-evidence - worker_01

## Boundary And Context Check

- Fallback used: `openai-codex / gpt-5.6-luna`, acting as bounded `worker_01`.
- Capability limitation: this pass performed DOM/browser rendering checks only. No screenshot/PPT/PDF, clinical, regulatory, or final visual acceptance was performed. Codex remains final authority.
- Read:
  - `context/ci-phase6-final-render-evidence_execution_context.md`
  - `plans/codex_execution_ci-phase6-final-render-evidence.md`
  - `tests/browser/test_b_portal.py`
  - Candidate `html.manifest.json`
  - Candidate `data/sitemap.json`
  - Candidate B portal CSS assets
- Candidate scanned read-only:
  - `output/acceptance/task-6.10/phase-6-acceptance-package-20260830/b-pnh/reports/B/v-fixture-b-pnh-001/html/`
- Candidate manifest digest: `f52daa3448845d41b3a2067fb5a660f292887b5b32300f6006df1407e5863075`
- No production files, candidate bytes, screenshots, or generated review artifacts were modified. The runner-managed report is not written by this worker.

## Work Performed

- Runtime:
  - Python `3.12.13`
  - Playwright `1.61.0`
  - Actual Chromium and WebKit launches succeeded.
- Full direct scan against the persisted candidate `file://` bytes:
  - Engines: Chromium, WebKit
  - Viewports: `1024`, `1280`, `1440`
  - Routes: all 24 sitemap routes
  - Total page/engine/viewport records: `2 × 3 × 24 = 144`
  - Each navigation waited for `domcontentloaded` plus 300 ms for chart rendering.
- Checked:
  - `main h1`, footer, and `html[lang="zh-CN"]`
  - Document/body horizontal dimensions
  - Visible element bounds and chart bounds
  - Chart and table-wrapper horizontal fit
  - Visible typography floors
  - Page errors, console errors, remote requests, request failures, bad responses
  - Visible internal/engineering labels and placeholders
  - Native `window.__CHART_GROUPS__` rows versus rendered table rows
  - Chart row IDs versus table row IDs and evidence-drawer availability
  - ECharts option values versus native fact values
  - Default safety and efficacy–safety matrix views
  - Expanded overview filter panel
  - Efficacy evidence drawer

Sitemap routes scanned:

```text
adherence.html
baseline-demographics.html
baseline-disease-context.html
baseline-overview.html
baseline-severity.html
disposition-overview.html
efficacy.html
efficacy-safety-matrix.html
evidence-limitations.html
longitudinal-results.html
loss-exit.html
overview.html
participant-flow.html
plan-deviation.html
product-trial-profiles.html
prohibited-medication.html
rescue-treatment.html
safety.html
screen-failure.html
subgroups-supporting-evidence.html
trial-exposure-context.html
products/iptacopan.html
trials/nct04558918.html
trials/nct04820530.html
```

## Artifacts And Evidence

No new artifact was authorized for this worker. Evidence is contained in this report for Codex review.

### Full-route loading and error results

| Check | Result |
|---|---:|
| Page/engine/viewport records | 144 |
| Navigation/evaluation failures | 0 |
| `main h1` / footer / `lang=zh-CN` contract failures | 0 |
| Page errors | 0 |
| Console errors | 0 |
| HTTP(S) remote requests | 0 |
| Request failures | 0 |
| Responses with status ≥400 | 0 |
| Engineering-label records | 0 |

Engineering-label scan included:

```text
baseline_sample_size
screen_failure
protocol_deviation
not_reported
factor-b
apply-cohort
24week
图形定位
先看图形，再核对完整数据表
规范化说明
comparable
numeric_value
row_id
trial_id
source_version_id
undefined
NaN
null
TODO
MVP
debug
placeholder
```

### Horizontal fit

- Document and body widths matched the viewport on all 144 records.
- Visible out-of-viewport elements: `0`.
- Contract-relevant chart geometry failures: `0`.
- Chart nodes checked: `558` total; `93` per engine/viewport combination.
- Table wrappers checked: `558`; maximum `scrollWidth - clientWidth`: `0`.
- Chart internal horizontal-fit failures: `0`.

Observed chart geometry was identical in Chromium and WebKit:

| Viewport | Chart left | Chart right | Chart width | Root/body width |
|---:|---:|---:|---:|---:|
| 1024 | 80.71875 | 943.28125 | 862.5625 | 1024 / 1024 |
| 1280 | 88.390625 | 1191.609375 | 1103.21875 | 1280 / 1280 |
| 1440 | 93.1875 | 1346.8125 | 1253.625 | 1440 / 1440 |

Chart heights ranged from `82.78125` to `340` px, with no zero-size or out-of-bounds chart.

The raw all-element `scrollWidth` enumeration found expected intrinsic widths on SVG `<text>`, clipped `.visually-hidden` labels, and responsive hidden `<thead>` elements. These were not visible layout overflow. Restricting the result to meaningful visible layout containers produced zero failures.

### Typography

- Minimum computed font size across all visible text-bearing elements: `16px` on all `144/144` records.
- `.kz-b-page-meta`: minimum `16px` on all `126` records where the selector exists.
- `.kz-chart-table__cell`: minimum `16px` on all `138` records where tables exist.
- `.kz-chart-table__th`: minimum `16px` on all `138` records where tables exist.
- Chart SVG text: minimum `16px` on all `126` records where SVG charts exist.
- No visible typography-floor failures.

Expected selector absences:

- Dossier routes do not use `.kz-b-page-meta`: `products/iptacopan.html`, both trial dossier routes.
- `subgroups-supporting-evidence.html` contains no chart table.
- Static/status-matrix routes do not contain SVG chart text.

### Data and chart consistency

- Native fact rows compared with rendered table rows: `4,638` observations; mismatches: `0`.
- Chart-table synchronization checks across six key pages, both engines, and all three widths: `36` records; failures: `0`.
- Evidence-drawer availability for rendered table rows: failures: `0`.
- Chart option value comparisons against native facts: `564` chart observations; failures: `0`.

Key values observed consistently in both engines and all widths:

- Efficacy:
  - APPLY-PNH treatment: `82.3%`, numerator `51`, denominator `60`
  - APPLY-PNH control: `1.8%`
  - APPOINT-PNH treatment: `92.2%`
- Safety:
  - APPLY treatment: `54.8%`
  - APPLY control: `60%`
  - APPOINT treatment: `60%`
  - APPOINT control: `不适用`
- Baseline sample size: `62`, `35`, `40`
- Baseline units: `人`, `岁`, `%`, `g/dL`
- Disposition values: `62`, `35`, `61`, `35`
- Matrix:
  - x-axis: `试验内疗效差（百分点）`
  - y-axis: `治疗组治疗期间不良事件发生率（%）`
  - y-axis inverse: `true`
  - APPLY-PNH bubble value: `80.5`
  - APPOINT-PNH limitation: `单臂研究没有试验内对照组，不计算治疗—对照疗效差`

### Targeted interaction evidence

Targeted checks: `24` records, covering both engines and all three widths.

- Overview filter expansion:
  - Opened successfully in all records.
  - Root/body width remained equal to viewport.
  - Visible out-of-bounds elements: none.
  - Chinese filter labels rendered; no engineering labels.
- Efficacy evidence drawer:
  - Drawer opened successfully in all records.
  - `分子 51` and `分母 60` visible in all records.
  - Internal labels absent.
- Safety default view:
  - Arms: `治疗组`, `对照组`
  - Trials: `伊普可泮 · APPLY-PNH`, `伊普可泮 · APPOINT-PNH`
  - `不适用` state visible.
  - All table wrappers fit.
- Matrix default view:
  - Correct axis names and inverted y-axis.
  - `80.5` visible.
  - Single-arm limitation visible.
  - Table wrapper fit.
- Targeted interaction event errors: `0`.

## Commands And Observations

- `functions.read`
  - Targeted execution context and plan: candidate path, digest, boundaries, work-item contract.
  - `tests/browser/test_b_portal.py`: confirmed Chromium/WebKit contract and expected widths/pages/assertions.
  - Candidate manifest and sitemap: confirmed current persisted artifact and 24 routes.
  - Candidate B CSS: confirmed `16px` chart/table/text floor and responsive overflow rules.
- `functions.eval`
  - Browser runtime probe: Chromium and WebKit both launched.
  - Full direct Playwright scan: `144` route/engine/viewport records; all contract-relevant failure counts were zero.
  - Targeted interaction scan: `24` records; all checks passed.
  - Chart-table synchronization scan: `36` records; all checks passed.
  - Native-fact-to-ECharts option scan: `564` chart observations; all checks passed.

Notable non-failure route types:

- `evidence-limitations.html`, `product-trial-profiles.html`, and `trials/nct04820530.html` expose static `status_matrix` blocks rather than ECharts instances. They rendered in bounds with no errors.
- `subgroups-supporting-evidence.html` contains no chart/table module; it still passed route, layout, typography, and error checks.

## Blockers Or Missing Environment

- No blocker for the assigned Chromium/WebKit scan.
- Both required engines were available and launched successfully.
- No package installation, credential handling, network access, or candidate modification was needed.
- Final screenshot/PPT/PDF/clinical/regulatory acceptance remains outside this worker’s capability and assignment.

## Rerun Requests Or Next Step

- No rerun requested while the candidate digest remains unchanged.
- Codex should bind this scan result to the candidate digest and review it alongside Worker 02 screenshot evidence and Worker 03 visual evidence JSON.
- If candidate bytes change, rerun the same `2 engines × 3 widths × 24 routes` matrix before final acceptance.
