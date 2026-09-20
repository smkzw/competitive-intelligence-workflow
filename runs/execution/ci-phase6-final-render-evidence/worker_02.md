# Execution Output: ci-phase6-final-render-evidence - worker_02

## Boundary And Context Check

- Fallback used: `openai-codex / gpt-5.6-luna`.
- Capability limitation: bounded screenshot/browser executor only. No final visual, PPT/PDF, clinical, regulatory, or delivery acceptance performed.
- Read initial context and plan:
  - `context/ci-phase6-final-render-evidence_execution_context.md`
  - `plans/codex_execution_ci-phase6-final-render-evidence.md`
- Additional scoped reads:
  - Candidate HTML manifest and directory.
  - `tests/browser/test_b_portal.py`.
  - Candidate `portal.js`, `report-b.js`, `charts.js`, and `evidence-drawer.js`.
  - `schemas/visual-render-evidence.schema.json`.
- Candidate inspected read-only:
  - `output/acceptance/task-6.10/phase-6-acceptance-package-20260830/b-pnh/reports/B/v-fixture-b-pnh-001/html/`
- Candidate digest bound in every record: `f52daa3448845d41b3a2067fb5a660f292887b5b32300f6006df1407e5863075`
- Snapshot ID: `snapshot-b-pnh-fixture-001`
- No production files or candidate HTML bytes modified.

## Work Performed

- Launched real Playwright Chromium `149.0.7827.55` and WebKit `26.5`.
- Playwright Python package: `1.61.0`; Python: `3.12.13`.
- Captured full-page PNGs for:
  - `overview`
  - `efficacy`
  - `safety`
  - `baseline-overview`
  - `disposition-overview`
  - `efficacy-safety-matrix`
- Viewports:
  - `1024 × 900`
  - `1440 × 900`
- Total screenshots: `2 engines × 6 pages × 2 widths = 24`.
- Capture context used `reduced_motion="reduce"` and waited 600 ms after `domcontentloaded`.
- Every screenshot record includes:
  - Engine, page, route, viewport, image dimensions.
  - Relative path and SHA-256.
  - Horizontal overflow and out-of-bounds counts.
  - Clipped, overlapping, and unreadable-label counts.
  - Visible-text scan and engineering-token scan.
  - Page-load, filtering, evidence-drawer, search, keyboard, and reduced-motion interaction checks.
- Visually inspected all 24 artifacts using in-memory PIL crops/full-length thumbnails. No additional inspection files were written.

## Artifacts And Evidence

Artifacts written only under the authorized candidate review directory:

- `reviews/visual-finalization/browser-metrics.json`
  - SHA-256: `c94ac1f0603b7855481fe73a9b1cd6779d7f882f1773e0dbe819fa2843e5cb68`
  - 24 records.
- `reviews/visual-finalization/screenshots/`
  - 24 PNGs.
  - Aggregate PNG size: `26,661,318` bytes.

Interaction status key: `L/F/D/S/K/R` = page load / filtering / drill-down / search / keyboard / reduced motion.

| Engine | Page | Viewport | Relative path | Screenshot SHA-256 | L/F/D/S/K/R |
|---|---|---:|---|---|---|
| chromium | overview | 1024×900 | `reviews/visual-finalization/screenshots/chromium/overview-1024.png` | `57d5d417af7a46aef7542d254eaaaed79830ea394292143d26379002b15f5f31` | pass / pass / pass / NA / fail / pass |
| chromium | efficacy | 1024×900 | `reviews/visual-finalization/screenshots/chromium/efficacy-1024.png` | `c9fc655d3721fe4413bb5a970e8c7fec9f794d4b0b8f8aca77a3d57134dd9f88` | pass / pass / pass / NA / fail / pass |
| chromium | safety | 1024×900 | `reviews/visual-finalization/screenshots/chromium/safety-1024.png` | `98d31a292c6ad434175cbd62c5ccb029d031b8ced2987353d13f9d1ea0eb7183` | pass / pass / pass / NA / fail / pass |
| chromium | baseline-overview | 1024×900 | `reviews/visual-finalization/screenshots/chromium/baseline-overview-1024.png` | `e65b1a1dd2eeb300359d6aa0713051ab4a71256c1bb0411919c954b17b0418cb` | pass / pass / pass / NA / fail / pass |
| chromium | disposition-overview | 1024×900 | `reviews/visual-finalization/screenshots/chromium/disposition-overview-1024.png` | `24322f1f950e7524854d1294ab9087d3fcf6a7ba2abf0e4fc0c78175f60d667e` | pass / pass / pass / NA / fail / pass |
| chromium | efficacy-safety-matrix | 1024×900 | `reviews/visual-finalization/screenshots/chromium/efficacy-safety-matrix-1024.png` | `0b530b1b983473fef2b248b7de5238ac13053557a30643bc64608ee5cdc806bc` | pass / pass / pass / NA / fail / pass |
| chromium | overview | 1440×900 | `reviews/visual-finalization/screenshots/chromium/overview-1440.png` | `205c43098f999cee1e1e1ffb96f22acc722245dabb6330a6468ac6bd40a51d8f` | pass / pass / pass / fail / fail / pass |
| chromium | efficacy | 1440×900 | `reviews/visual-finalization/screenshots/chromium/efficacy-1440.png` | `a1f2d46ecef1cebc090775efb46988533cc4cf095f0788f3f73a06524eab0f65` | pass / pass / pass / fail / fail / pass |
| chromium | safety | 1440×900 | `reviews/visual-finalization/screenshots/chromium/safety-1440.png` | `ba71611e145a1e45795a8a998e7c20c82b91ff8b4f342f9664c392765c18957f` | pass / pass / pass / fail / fail / pass |
| chromium | baseline-overview | 1440×900 | `reviews/visual-finalization/screenshots/chromium/baseline-overview-1440.png` | `bef72525673d4a3e12fdefb9750a6ca9738f95be7d7d9103035cff1eb0464958` | pass / pass / pass / fail / fail / pass |
| chromium | disposition-overview | 1440×900 | `reviews/visual-finalization/screenshots/chromium/disposition-overview-1440.png` | `09f658b7efa8b37ded5c7c907bad8e4c8d2637c0cc9c9c4e72bff367685fa956` | pass / pass / pass / fail / fail / pass |
| chromium | efficacy-safety-matrix | 1440×900 | `reviews/visual-finalization/screenshots/chromium/efficacy-safety-matrix-1440.png` | `1026711cf9cbc0bc6ea17f05fe1687882d6613e615ececc19bf0cc0b265f6e20` | pass / pass / pass / fail / fail / pass |
| webkit | overview | 1024×900 | `reviews/visual-finalization/screenshots/webkit/overview-1024.png` | `6cad47217c8b58ea1721b1e607351496b971bdefc9a34f0c13f85deb51e19c8f` | pass / pass / pass / NA / fail / pass |
| webkit | efficacy | 1024×900 | `reviews/visual-finalization/screenshots/webkit/efficacy-1024.png` | `df8f095a2ea9907b4eb4e5ce6a152acb05a34c14bc8257254a72837c3cef7946` | pass / pass / pass / NA / fail / pass |
| webkit | safety | 1024×900 | `reviews/visual-finalization/screenshots/webkit/safety-1024.png` | `7f2fc0b8cfe0ef6f6004cc57c80cf72cd6fbb1d26e3f12f8d8e39afb23a9984e` | pass / pass / pass / NA / fail / pass |
| webkit | baseline-overview | 1024×900 | `reviews/visual-finalization/screenshots/webkit/baseline-overview-1024.png` | `3983e1d22bc58bfff5de68f3225a064c433f8b411b2fd94f091d6cbe690b8d46` | pass / pass / pass / NA / fail / pass |
| webkit | disposition-overview | 1024×900 | `reviews/visual-finalization/screenshots/webkit/disposition-overview-1024.png` | `f975f8c2a8fdb6e007ea1c483c088b921ec248ecaf5d35b16f9a00d77f5d7e7f` | pass / pass / pass / NA / fail / pass |
| webkit | efficacy-safety-matrix | 1024×900 | `reviews/visual-finalization/screenshots/webkit/efficacy-safety-matrix-1024.png` | `96b1db454b250f96c0d44f8efb7b4f2d50c17e729ce8ad14273c6caccef3c094` | pass / pass / pass / NA / fail / pass |
| webkit | overview | 1440×900 | `reviews/visual-finalization/screenshots/webkit/overview-1440.png` | `1587e117a625e35516a1c3dad2fc4990c6f01ddd9b81505ec5167b6f0fe88b2f` | pass / pass / pass / pass / fail / pass |
| webkit | efficacy | 1440×900 | `reviews/visual-finalization/screenshots/webkit/efficacy-1440.png` | `10f5ec515b5d462a9a102ccee9c49efa5b02730104f9b32b65f04d0b5110663e` | pass / pass / pass / pass / fail / pass |
| webkit | safety | 1440×900 | `reviews/visual-finalization/screenshots/webkit/safety-1440.png` | `2063c29efe44f4dde16869142b1b4124e9074638712ada3ca20bc8ad58d30745` | pass / pass / pass / pass / fail / pass |
| webkit | baseline-overview | 1440×900 | `reviews/visual-finalization/screenshots/webkit/baseline-overview-1440.png` | `781e2993a6ee685c29b9ddeb83b1166b8a8a63ed875d83d37103b14d69e4dfb8` | pass / pass / pass / pass / fail / pass |
| webkit | disposition-overview | 1440×900 | `reviews/visual-finalization/screenshots/webkit/disposition-overview-1440.png` | `8d6c68957790715af7e52ae5ba87f99746608a3a1f1e3da5f5dc3ddf9a90ed90` | pass / pass / pass / pass / fail / pass |
| webkit | efficacy-safety-matrix | 1440×900 | `reviews/visual-finalization/screenshots/webkit/efficacy-safety-matrix-1440.png` | `819a90e8c56b0d6db3f1d5b6b31b77734cfbfff141b2c844a55b24fab971c026` | pass / pass / pass / pass / fail / pass |

Machine observations across all 24 records:

- Horizontal overflow delta: `0` in all records.
- Visible out-of-bounds elements: `0`.
- Clipped-label count: `0`.
- Meaningful chart-label overlap count: `0`.
- Unreadable-label count: `0`.
- Minimum visible label font size: `16px`.
- Missing required visible terms: `0`.
- Engineering/internal visible tokens: `0`.
- Screenshot files exist and all recorded SHA-256 values match.
- All page-load structural checks passed.
- All filtering checks passed.
- All click-based evidence-drawer checks passed.
- Reduced-motion media query matched and active animations were `0` in all records.

Visual observations as a Chinese clinical medical manager:

- `overview` and `efficacy`: APPLY-PNH/APPOINT-PNH, 第24周, 82.3, 1.8, and 92.2 are visible in the chart/table presentation.
- `safety`: heatmaps visibly retain numeric values and striped `不适用` state; safety-event labels and treatment-window wording are present.
- `baseline-overview`: separate 人、岁、%、g/dL views are visible; two-line category labels remain readable.
- `disposition-overview`: status bars and tables visibly distinguish 已筛选、已随机、已接受治疗、完成治疗、完成研究 and 未公开 states.
- `efficacy-safety-matrix`: APPLY-PNH bubble at 80.5, axis labels, and APPOINT-PNH single-arm limitation are visible.
- 1024 layouts switch to long card/table presentation; 1440 layouts use wider table rows. No visual clipping was observed in the inspected crops/full-page thumbnails.

## Commands And Observations

- `functions.read`
  - Confirmed candidate path, manifest digest, snapshot, and page routes.
  - Read browser contract and interaction selectors.
  - Read evidence drawer and chart/report keyboard handlers.
- `functions.glob`
  - Located project `.venv` and confirmed the authorized review directory was initially absent.
  - Confirmed exactly 24 PNG artifacts after capture.
- `functions.grep`
  - Confirmed the candidate `report-b.js:429-437` cell keydown handler calls `activateRow(rowId, td)`.
  - Confirmed `report-b.js` does not define `activateRow`; `charts.js` contains a separate private implementation.
- Initial shell probe:
  - `python -c ...` failed because `python` is not on PATH.
  - Project `.venv` was available; no installation was performed.
- `functions.eval`
  - Imported Playwright from `.venv`.
  - Launched real Chromium and WebKit.
  - Executed full-page screenshot capture and DOM metrics collection.
  - Exercised filtering, evidence drawer, search, keyboard, and reduced-motion paths.
  - Calculated screenshot SHA-256 values and wrote `browser-metrics.json`.
  - Used PIL only in memory for visual inspection; no inspection derivatives were created.
- WebKit `file://` navigation returned status `0`; this was recorded as an accepted successful local-file response. Chromium returned status `200`.
- No project-wide tests were run; this worker scope was browser capture and interaction evidence only.

## Blockers Or Missing Environment

- Environment blocker: none. Both required engines launched successfully from the existing `.venv`; no package installation, credentials, network access, or server was needed.
- Candidate interaction issue requiring Codex review:
  - All 24 keyboard evidence-cell probes emitted one runtime page error.
  - Chromium: `activateRow is not defined` — 12 records.
  - WebKit: `Can't find variable: activateRow` — 12 records.
  - The evidence drawer still became visible and Escape closed it, but the keyboard path is not error-free.
  - A targeted fresh-load probe showed no error before keyboard interaction; the error appears after evidence-cell Enter.
- Search interaction issue:
  - At 1024, the global search input is not visible and is recorded as `not_applicable`.
  - WebKit 1440 search passed.
  - Chromium 1440 returned 10 results and focused one result, but after Escape the native `input[type=search]` behavior reopened the results list; six Chromium 1440 search checks are recorded as failed.
- These are candidate behavior findings, not final acceptance conclusions. No source fix was made under the read-only boundary.

## Rerun Requests Or Next Step

1. Codex should decide whether the `activateRow` keyboard runtime error blocks acceptance. If yes, remove or repair the duplicate/stale handler in the candidate source, then rerun all 24 capture records.
2. Codex should decide whether Chromium’s Escape behavior must leave search results hidden. If yes, repair the search/input interaction and rerun the six Chromium 1440 search records, preferably followed by the full 24-record capture.
3. Worker 03 may consume the current screenshots and `browser-metrics.json`, but should preserve the recorded keyboard/search failures and must not convert this worker output into an independent final verdict.
