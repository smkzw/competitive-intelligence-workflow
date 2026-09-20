# Visual Execution Follow-up: worker_01

## Current Candidate

- Repaired candidate:
  - `output/acceptance/task-6.10/phase-6-acceptance-package-20260830/b-pnh-interaction-repair-20260830/reports/B/v-fixture-b-pnh-001/html/`
- Manifest digest verified: `f094848b41cf9c66ae8c3ecfb58e0305d5a531f477e6e6cdaa5e05ea3694060e`
- Sitemap routes: `24`
- Read initial follow-up set:
  - `context/ci-phase6-final-render-evidence_execution_context.md`
  - `runs/execution/ci-phase6-final-render-evidence/worker_01.md`
  - `runs/execution/ci-phase6-interaction-repair/worker_03.md`
- Candidate remained read-only. No screenshots, formal JSON, or candidate files were created or modified.

## Full Scan

Fresh Playwright `1.61.0` direct scan against the repaired candidate’s `file://` bytes:

- Engines: Chromium, WebKit
- Viewports: `1024`, `1280`, `1440`
- Routes per engine/viewport: `24`
- Total route/engine/viewport records: `144`
- Navigation/evaluation failures: `0`

| Check | Result |
|---|---:|
| Page errors | 0 |
| Console errors | 0 |
| HTTP(S) remote requests | 0 |
| Request failures | 0 |
| Responses with status ≥400 | 0 |
| `main h1` / footer / `lang="zh-CN"` failures | 0 |
| Page-level horizontal overflow failures | 0 |
| Visible out-of-viewport elements | 0 |
| Meaningful layout-container overflow failures | 0 |
| Chart geometry failures | 0 |
| Table-wrapper overflow failures | 0 |
| Visible typography-floor failures | 0 |
| Visible internal/engineering-label findings | 0 |
| Native fact/table mismatches | 0 |

### Exact geometry totals

- Chart nodes checked: `558` total, `93` per engine/viewport.
- Table wrappers checked: `558`.
- Maximum table-wrapper `scrollWidth - clientWidth`: `0`.
- Root/body widths matched the viewport for all `144/144` records.

| Engine | Width | Root/body width | Chart bounds | Chart width |
|---|---:|---:|---:|---:|
| Chromium | 1024 | `1024 / 1024` | `80.71875–943.28125` | `862.5625` |
| Chromium | 1280 | `1280 / 1280` | `88.390625–1191.609375` | `1103.21875` |
| Chromium | 1440 | `1440 / 1440` | `93.1875–1346.8125` | `1253.625` |
| WebKit | 1024 | `1024 / 1024` | `80.71875–943.28125` | `862.5625` |
| WebKit | 1280 | `1280 / 1280` | `88.390625–1191.609375` | `1103.21875` |
| WebKit | 1440 | `1440 / 1440` | `93.1875–1346.8125` | `1253.625` |

### Font and label scan

- Minimum computed font size across visible text: `16px` on `144/144` records.
- `.kz-b-page-meta`: minimum `16px` wherever present.
- `.kz-chart-table__cell` and `.kz-chart-table__th`: minimum `16px` wherever present.
- Chart SVG text: minimum `16px` wherever present.
- Engineering-label scan: `0` findings.

### Key chart/table consistency

- Native fact rows compared with rendered tables: `4,638` observations; mismatches `0`.
- Chart/table synchronization checks: `36` records; failures `0`.
- Native facts versus ECharts options: `564` chart observations; failures `0`.

Observed values remained consistent:

- Efficacy: `82.3%` with `51/60`, APPLY control `1.8%`, APPOINT treatment `92.2%`.
- Safety: `54.8%`, `60%`, `60%`, APPOINT control `不适用`.
- Baseline sample sizes: `62`, `35`, `40`; units `人`, `岁`, `%`, `g/dL`.
- Disposition: `62`, `35`, `61`, `35`.
- Matrix:
  - x-axis: `试验内疗效差（百分点）`
  - y-axis: `治疗组治疗期间不良事件发生率（%）`
  - y-axis inverse: `true`
  - APPLY-PNH value: `80.5`

Expected static route behavior remained unchanged: three routes expose static `status_matrix` blocks instead of ECharts; `subgroups-supporting-evidence.html` has no chart/table module. Neither is a failure.

## Interaction Regression

### Evidence-cell keyboard probes

At desktop viewport `1440`:

- Engines: Chromium, WebKit
- Keys: `Enter`, `Space`
- Total probes: `4`
- Evidence cell count: `1` for every probe.
- Drawer visible/open: `true` for every probe.
- Open row: `eff-row-nct04558918-apply-treatment` for every probe.
- Page errors: `0`
- Console errors: `0`
- Remote requests: `0`

### Desktop search Escape probes

At desktop viewport `1440`:

- Engines: Chromium, WebKit
- Total probes: `2`
- Search query: `疗效`
- Search result count before Escape: `10` in both engines.
- Results hidden after Escape: yes.
- Visible results after Escape: `0`.
- Page errors: `0`
- Console errors: `0`
- Remote requests: `0`

Combined interaction probes: `6` records, all passed with zero captured errors.

## Remaining Boundary

- No unexpected result was observed in the repaired-candidate follow-up scan.
- This worker performed browser/DOM verification only; no screenshot, PPT/PDF, clinical, regulatory, or final visual acceptance is claimed.
- Codex remains responsible for final acceptance and for binding this follow-up evidence to the repaired digest.
- If the candidate bytes change, rerun the same `2 engines × 3 widths × 24 routes` scan and the six interaction probes.
