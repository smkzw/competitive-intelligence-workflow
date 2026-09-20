# Visual Execution Follow-up: worker_02

## Current Candidate

- Candidate:
  `output/acceptance/task-6.10/phase-6-acceptance-package-20260830/b-pnh-interaction-repair-20260830`
- HTML:
  `reports/B/v-fixture-b-pnh-001/html`
- Manifest:
  `reports/B/v-fixture-b-pnh-001/html.manifest.json`
- Candidate digest bound in every metrics record:

  `f094848b41cf9c66ae8c3ecfb58e0305d5a531f477e6e6cdaa5e05ea3694060e`

- Snapshot ID: `snapshot-b-pnh-fixture-001`
- Manifest file SHA-256:
  `7eaecdeb24883fa7d72a44114f5b891d72f6de4d2328cafaac6d7212f13c92c9`
- Read the updated execution context, prior Worker 02 report, and Worker 03 interaction-repair report.
- Old failure candidate `b-pnh/` was not modified or copied.

## Screenshot And Interaction Evidence

Fresh capture details:

- Real Chromium `149.0.7827.55`
- Real WebKit `26.5`
- Playwright Python `1.61.0`
- Viewports: `1024×900` and `1440×900`
- Full-page PNGs, reduced-motion context
- 24 records: 2 engines × 6 pages × 2 widths
- Keyboard probes included both `Enter` and `Space`
- Focus visibility was explicitly checked
- Desktop search query: `疗效`; ArrowDown focus state and Escape close state checked

`L/F/D/S/K/V/R` = page load / filtering / evidence drawer / search / keyboard Enter+Space / focus visibility / reduced motion. `NA` means search input is not visible at that responsive width.

| Engine | Width | Page | Relative PNG | SHA-256 | Image | L/F/D/S/K/V/R | Response |
|---|---:|---|---|---|---:|---|---:|
| chromium | 1024 | overview | `reviews/visual-finalization/screenshots/chromium/overview-1024.png` | `57d5d417af7a46aef7542d254eaaaed79830ea394292143d26379002b15f5f31` | 1024×34344 | pass/pass/pass/NA/pass/pass/pass | 200 |
| chromium | 1024 | efficacy | `reviews/visual-finalization/screenshots/chromium/efficacy-1024.png` | `c9fc655d3721fe4413bb5a970e8c7fec9f794d4b0b8f8aca77a3d57134dd9f88` | 1024×2751 | pass/pass/pass/NA/pass/pass/pass | 200 |
| chromium | 1024 | safety | `reviews/visual-finalization/screenshots/chromium/safety-1024.png` | `b489889c56f265b92e9ad5b3900f0ad67d198488793a05237c24667f8181a1d7` | 1024×7367 | pass/pass/pass/NA/pass/pass/pass | 200 |
| chromium | 1024 | baseline-overview | `reviews/visual-finalization/screenshots/chromium/baseline-overview-1024.png` | `e65b1a1dd2eeb300359d6aa0713051ab4a71256c1bb0411919c954b17b0418cb` | 1024×6496 | pass/pass/pass/NA/pass/pass/pass | 200 |
| chromium | 1024 | disposition-overview | `reviews/visual-finalization/screenshots/chromium/disposition-overview-1024.png` | `24322f1f950e7524854d1294ab9087d3fcf6a7ba2abf0e4fc0c78175f60d667e` | 1024×18071 | pass/pass/pass/NA/pass/pass/pass | 200 |
| chromium | 1024 | efficacy-safety-matrix | `reviews/visual-finalization/screenshots/chromium/efficacy-safety-matrix-1024.png` | `0b530b1b983473fef2b248b7de5238ac13053557a30643bc64608ee5cdc806bc` | 1024×1936 | pass/pass/pass/NA/pass/pass/pass | 200 |
| chromium | 1440 | overview | `reviews/visual-finalization/screenshots/chromium/overview-1440.png` | `205c43098f999cee1e1e1ffb96f22acc722245dabb6330a6468ac6bd40a51d8f` | 1440×12425 | pass/pass/pass/pass/pass/pass/pass | 200 |
| chromium | 1440 | efficacy | `reviews/visual-finalization/screenshots/chromium/efficacy-1440.png` | `a1f2d46ecef1cebc090775efb46988533cc4cf095f0788f3f73a06524eab0f65` | 1440×2072 | pass/pass/pass/pass/pass/pass/pass | 200 |
| chromium | 1440 | safety | `reviews/visual-finalization/screenshots/chromium/safety-1440.png` | `af73665e775e0459bc1555bb06e7736d54ffb2281f9f13e8d19712da8bbbbf68` | 1440×3414 | pass/pass/pass/pass/pass/pass/pass | 200 |
| chromium | 1440 | baseline-overview | `reviews/visual-finalization/screenshots/chromium/baseline-overview-1440.png` | `bef72525673d4a3e12fdefb9750a6ca9738f95be7d7d9103035cff1eb0464958` | 1440×3577 | pass/pass/pass/pass/pass/pass/pass | 200 |
| chromium | 1440 | disposition-overview | `reviews/visual-finalization/screenshots/chromium/disposition-overview-1440.png` | `09f658b7efa8b37ded5c7c907bad8e4c8d2637c0cc9c9c4e72bff367685fa956` | 1440×4206 | pass/pass/pass/pass/pass/pass/pass | 200 |
| chromium | 1440 | efficacy-safety-matrix | `reviews/visual-finalization/screenshots/chromium/efficacy-safety-matrix-1440.png` | `1026711cf9cbc0bc6ea17f05fe1687882d6613e615ececc19bf0cc0b265f6e20` | 1440×1473 | pass/pass/pass/pass/pass/pass/pass | 200 |
| webkit | 1024 | overview | `reviews/visual-finalization/screenshots/webkit/overview-1024.png` | `6cad47217c8b58ea1721b1e607351496b971bdefc9a34f0c13f85deb51e19c8f` | 1024×34344 | pass/pass/pass/NA/pass/pass/pass | 0 |
| webkit | 1024 | efficacy | `reviews/visual-finalization/screenshots/webkit/efficacy-1024.png` | `df8f095a2ea9907b4eb4e5ce6a152acb05a34c14bc8257254a72837c3cef7946` | 1024×2751 | pass/pass/pass/NA/pass/pass/pass | 0 |
| webkit | 1024 | safety | `reviews/visual-finalization/screenshots/webkit/safety-1024.png` | `7f2fc0b8cfe0ef6f6004cc57c80cf72cd6fbb1d26e3f12f8d8e39afb23a9984e` | 1024×7367 | pass/pass/pass/NA/pass/pass/pass | 0 |
| webkit | 1024 | baseline-overview | `reviews/visual-finalization/screenshots/webkit/baseline-overview-1024.png` | `3983e1d22bc58bfff5de68f3225a064c433f8b411b2fd94f091d6cbe690b8d46` | 1024×6496 | pass/pass/pass/NA/pass/pass/pass | 0 |
| webkit | 1024 | disposition-overview | `reviews/visual-finalization/screenshots/webkit/disposition-overview-1024.png` | `f975f8c2a8fdb6e007ea1c483c088b921ec248ecaf5d35b16f9a00d77f5d7e7f` | 1024×18071 | pass/pass/pass/NA/pass/pass/pass | 0 |
| webkit | 1024 | efficacy-safety-matrix | `reviews/visual-finalization/screenshots/webkit/efficacy-safety-matrix-1024.png` | `96b1db454b250f96c0d44f8efb7b4f2d50c17e729ce8ad14273c6caccef3c094` | 1024×1936 | pass/pass/pass/NA/pass/pass/pass | 0 |
| webkit | 1440 | overview | `reviews/visual-finalization/screenshots/webkit/overview-1440.png` | `1587e117a625e35516a1c3dad2fc4990c6f01ddd9b81505ec5167b6f0fe88b2f` | 1440×12425 | pass/pass/pass/pass/pass/pass/pass | 0 |
| webkit | 1440 | efficacy | `reviews/visual-finalization/screenshots/webkit/efficacy-1440.png` | `10f5ec515b5d462a9a102ccee9c49efa5b02730104f9b32b65f04d0b5110663e` | 1440×2072 | pass/pass/pass/pass/pass/pass/pass | 0 |
| webkit | 1440 | safety | `reviews/visual-finalization/screenshots/webkit/safety-1440.png` | `2063c29efe44f4dde16869142b1b4124e9074638712ada3ca20bc8ad58d30745` | 1440×3414 | pass/pass/pass/pass/pass/pass/pass | 0 |
| webkit | 1440 | baseline-overview | `reviews/visual-finalization/screenshots/webkit/baseline-overview-1440.png` | `781e2993a6ee685c29b9ddeb83b1166b8a8a63ed875d83d37103b14d69e4dfb8` | 1440×3577 | pass/pass/pass/pass/pass/pass/pass | 0 |
| webkit | 1440 | disposition-overview | `reviews/visual-finalization/screenshots/webkit/disposition-overview-1440.png` | `8d6c68957790715af7e52ae5ba87f99746608a3a1f1e3da5f5dc3ddf9a90ed90` | 1440×4206 | pass/pass/pass/pass/pass/pass/pass | 0 |
| webkit | 1440 | efficacy-safety-matrix | `reviews/visual-finalization/screenshots/webkit/efficacy-safety-matrix-1440.png` | `819a90e8c56b0d6db3f1d5b6b31b77734cfbfff141b2c844a55b24fab971c026` | 1440×1473 | pass/pass/pass/pass/pass/pass/pass | 0 |

Metrics artifact:

```text
reviews/visual-finalization/browser-metrics.json
bytes: 207132
sha256: 5209214e062cf7f8d1e6dd03d293b53123893ba56863f797c9250c63d6d4f2178
```

Integrity and machine checks:

- Records: `24`
- PNGs: `24`
- Missing PNGs: `0`
- Screenshot hash mismatches: `0`
- Duplicate paths: `0`
- Candidate digest mismatch: `0`
- Page load: `24/24`
- Filtering: `24/24`
- Evidence drawer: `24/24`
- Keyboard Enter and Space activation: `24/24`
- Focus visibility: `24/24`
- Reduced motion: `24/24`
- Desktop search: `12/12` at 1440; `12` not applicable at 1024 because the input is hidden responsively
- Page/console/request/runtime errors: `0`
- Horizontal overflow delta: `0` for all records
- Clipped labels: `0`
- Chart-label overlaps: `0`
- Unreadable labels: `0`
- Missing required clinical terms: `0`
- Engineering/debug labels: `0`

WebKit reports response status `0` for local `file://` navigation; the runner records this as accepted local-file behavior. Chromium reports status `200`.

## Visual Findings

All 24 fresh screenshots were visually inspected. Complete full-page thumbnails were checked for the long `overview` and `disposition-overview` pages; page-top and chart/table regions were inspected for every route and engine/width combination.

Observed:

- `overview` and `efficacy`: Chinese clinical headings, APPLY-PNH/APPOINT-PNH, week-24 context, treatment/control charts, and supporting tables are visible.
- `safety`: numeric heatmaps remain visible; striped `不适用` states are visually distinct from reported values.
- `baseline-overview`: baseline sample size, hemoglobin, demographic units, and multiline Chinese categories remain readable.
- `disposition-overview`: flow bars and tables distinguish `已筛选`, `已随机`, `已接受治疗`, `完成治疗`, and `完成研究`.
- `efficacy-safety-matrix`: axes, matrix labels, the `80.5` value, and the APPOINT-PNH single-arm limitation note are visible.
- At 1024 px, the layout becomes a longer card/table presentation; at 1440 px, tables use wider rows. No visible horizontal clipping, label collision, or unreadable clinical text was observed.

## Remaining Boundary

- This report is execution evidence only. It is not a formal visual-render plan, independent review conclusion, clinical/regulatory assessment, or final acceptance verdict.
- No production source, fixture, package index, Trellis record, or old failure candidate was modified.
- No environment blocker remained; existing virtual-environment Playwright and both browser engines were usable without installation or network access.
- The 1024 px search result is `NA` by responsive design because the search control is not visible there.
- Codex retains final review, candidate promotion, and delivery-state authority.
