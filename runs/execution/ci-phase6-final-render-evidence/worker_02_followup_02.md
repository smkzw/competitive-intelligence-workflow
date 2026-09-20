# Visual Execution Follow-up 2: worker_02

## Matrix Completion

Current repaired candidate:

```text
output/acceptance/task-6.10/phase-6-acceptance-package-20260830/b-pnh-interaction-repair-20260830
```

HTML artifact:

```text
reports/B/v-fixture-b-pnh-001/html
candidate digest: f094848b41cf9c66ae8c3ecfb58e0305d5a531f477e6e6cdaa5e05ea3694060e
snapshot: snapshot-b-pnh-fixture-001
```

Completed render matrix:

- Chromium/WebKit.
- Widths `768`, `1024`, `1440`.
- Six pages at each engine/width.
- `36` default full-page render records.
- Existing 24 default screenshots at 1024/1440 retained with unchanged hashes.
- Added 12 fresh 768 default screenshots.
- All 36 records bind to the repaired candidate digest.

Status key: `L/F/D/S/K/FV/R` = page load / filtering / evidence drawer / search / keyboard Enter+Space / focus visibility / reduced motion.

| Engine | Page | Viewport | Screenshot | SHA-256 | Image | Status |
|---|---|---:|---|---|---:|---|
| chromium | overview | 1024×900 | `reviews/visual-finalization/screenshots/chromium/overview-1024.png` | `57d5d417af7a46aef7542d254eaaaed79830ea394292143d26379002b15f5f31` | 1024×34344 | P/P/P/P/P/P/P |
| chromium | efficacy | 1024×900 | `reviews/visual-finalization/screenshots/chromium/efficacy-1024.png` | `c9fc655d3721fe4413bb5a970e8c7fec9f794d4b0b8f8aca77a3d57134dd9f88` | 1024×2751 | P/P/P/P/P/P/P |
| chromium | safety | 1024×900 | `reviews/visual-finalization/screenshots/chromium/safety-1024.png` | `b489889c56f265b92e9ad5b3900f0ad67d198488793a05237c24667f8181a1d7` | 1024×7367 | P/P/P/P/P/P/P |
| chromium | baseline-overview | 1024×900 | `reviews/visual-finalization/screenshots/chromium/baseline-overview-1024.png` | `e65b1a1dd2eeb300359d6aa0713051ab4a71256c1bb0411919c954b17b0418cb` | 1024×6496 | P/P/P/P/P/P/P |
| chromium | disposition-overview | 1024×900 | `reviews/visual-finalization/screenshots/chromium/disposition-overview-1024.png` | `24322f1f950e7524854d1294ab9087d3fcf6a7ba2abf0e4fc0c78175f60d667e` | 1024×18071 | P/P/P/P/P/P/P |
| chromium | efficacy-safety-matrix | 1024×900 | `reviews/visual-finalization/screenshots/chromium/efficacy-safety-matrix-1024.png` | `0b530b1b983473fef2b248b7de5238ac13053557a30643bc64608ee5cdc806bc` | 1024×1936 | P/P/P/P/P/P/P |
| chromium | overview | 1440×900 | `reviews/visual-finalization/screenshots/chromium/overview-1440.png` | `205c43098f999cee1e1e1ffb96f22acc722245dabb6330a6468ac6bd40a51d8f` | 1440×12425 | P/P/P/P/P/P/P |
| chromium | efficacy | 1440×900 | `reviews/visual-finalization/screenshots/chromium/efficacy-1440.png` | `a1f2d46ecef1cebc090775efb46988533cc4cf095f0788f3f73a06524eab0f65` | 1440×2072 | P/P/P/P/P/P/P |
| chromium | safety | 1440×900 | `reviews/visual-finalization/screenshots/chromium/safety-1440.png` | `af73665e775e0459bc1555bb06e7736d54ffb2281f9f13e8d19712da8bbbbf68` | 1440×3414 | P/P/P/P/P/P/P |
| chromium | baseline-overview | 1440×900 | `reviews/visual-finalization/screenshots/chromium/baseline-overview-1440.png` | `bef72525673d4a3e12fdefb9750a6ca9738f95be7d7d9103035cff1eb0464958` | 1440×3577 | P/P/P/P/P/P/P |
| chromium | disposition-overview | 1440×900 | `reviews/visual-finalization/screenshots/chromium/disposition-overview-1440.png` | `09f658b7efa8b37ded5c7c907bad8e4c8d2637c0cc9c9c4e72bff367685fa956` | 1440×4206 | P/P/P/P/P/P/P |
| chromium | efficacy-safety-matrix | 1440×900 | `reviews/visual-finalization/screenshots/chromium/efficacy-safety-matrix-1440.png` | `1026711cf9cbc0bc6ea17f05fe1687882d6613e615ececc19bf0cc0b265f6e20` | 1440×1473 | P/P/P/P/P/P/P |
| webkit | overview | 1024×900 | `reviews/visual-finalization/screenshots/webkit/overview-1024.png` | `6cad47217c8b58ea1721b1e607351496b971bdefc9a34f0c13f85deb51e19c8f` | 1024×34344 | P/P/P/P/P/P/P |
| webkit | efficacy | 1024×900 | `reviews/visual-finalization/screenshots/webkit/efficacy-1024.png` | `df8f095a2ea9907b4eb4e5ce6a152acb05a34c14bc8257254a72837c3cef7946` | 1024×2751 | P/P/P/P/P/P/P |
| webkit | safety | 1024×900 | `reviews/visual-finalization/screenshots/webkit/safety-1024.png` | `7f2fc0b8cfe0ef6f6004cc57c80cf72cd6fbb2fd94f091d6cbe690b8d46` | 1024×7367 | P/P/P/P/P/P/P |
| webkit | baseline-overview | 1024×900 | `reviews/visual-finalization/screenshots/webkit/baseline-overview-1024.png` | `3983e1d22bc58bfff5de68f3225a064c433f8b411b2fd94f091d6cbe690b8d46` | 1024×6496 | P/P/P/P/P/P/P |
| webkit | disposition-overview | 1024×900 | `reviews/visual-finalization/screenshots/webkit/disposition-overview-1024.png` | `f975f8c2a8fdb6e007ea1c483c088b921ec248ecaf5d35b16f9a00d77f5d7e7f` | 1024×18071 | P/P/P/P/P/P/P |
| webkit | efficacy-safety-matrix | 1024×900 | `reviews/visual-finalization/screenshots/webkit/efficacy-safety-matrix-1024.png` | `96b1db454b250f96c0d44f8efb7b4f2d50c17e729ce8ad14273c6caccef3c094` | 1024×1936 | P/P/P/P/P/P/P |
| webkit | overview | 1440×900 | `reviews/visual-finalization/screenshots/webkit/overview-1440.png` | `1587e117a625e35516a1c3dad2fc4990c6f01ddd9b81505ec5167b6f0fe88b2f` | 1440×12425 | P/P/P/P/P/P/P |
| webkit | efficacy | 1440×900 | `reviews/visual-finalization/screenshots/webkit/efficacy-1440.png` | `10f5ec515b5d462a9a102ccee9c49efa5b02730104f9b32b65f04d0b5110663e` | 1440×2072 | P/P/P/P/P/P/P |
| webkit | safety | 1440×900 | `reviews/visual-finalization/screenshots/webkit/safety-1440.png` | `2063c29efe44f4dde16869142b1b4124e9074638712ada3ca20bc8ad58d30745` | 1440×3414 | P/P/P/P/P/P/P |
| webkit | baseline-overview | 1440×900 | `reviews/visual-finalization/screenshots/webkit/baseline-overview-1440.png` | `781e2993a6ee685c29b9ddeb83b1166b8a8a63ed875d83d37103b14d69e4dfb8` | 1440×3577 | P/P/P/P/P/P/P |
| webkit | disposition-overview | 1440×900 | `reviews/visual-finalization/screenshots/webkit/disposition-overview-1440.png` | `8d6c68957790715af7e52ae5ba87f99746608a3a1f1e3da5f5dc3ddf9a90ed90` | 1440×4206 | P/P/P/P/P/P/P |
| webkit | efficacy-safety-matrix | 1440×900 | `reviews/visual-finalization/screenshots/webkit/efficacy-safety-matrix-1440.png` | `819a90e8c56b0d6db3f1d5b6b31b77734cfbfff141b2c844a55b24fab971c026` | 1440×1473 | P/P/P/P/P/P/P |
| chromium | overview | 768×900 | `reviews/visual-finalization/screenshots/chromium/overview-768.png` | `44606229f314cb896feaf2f22df511c6fa0d6116d97b1bee2ce6e8f98d3ec097` | 768×15461 | P/P/P/P/P/P/P |
| chromium | efficacy | 768×900 | `reviews/visual-finalization/screenshots/chromium/efficacy-768.png` | `70e4c98c935435d1b301a01b9da2f2dc611f4c9838d6104fb4387bc0dff9850f` | 768×2575 | P/P/P/P/P/P/P |
| chromium | safety | 768×900 | `reviews/visual-finalization/screenshots/chromium/safety-768.png` | `df33f891fd5feea41ed1f27595af2c821bf7e7b0e767c14114569f3da0de84f5` | 768×3905 | P/P/P/P/P/P/P |
| chromium | baseline-overview | 768×900 | `reviews/visual-finalization/screenshots/chromium/baseline-overview-768.png` | `607d356c03eb19056f20f48bd0311eae90e94018532b3db3e63f0aaad1d081b0` | 768×3869 | P/P/P/P/P/P/P |
| chromium | disposition-overview | 768×900 | `reviews/visual-finalization/screenshots/chromium/disposition-overview-768.png` | `86978fc3e58b5e2b451841302020ccdfdf4947718cab27a05fe2538b0963af4c` | 768×5738 | P/P/P/P/P/P/P |
| chromium | efficacy-safety-matrix | 768×900 | `reviews/visual-finalization/screenshots/chromium/efficacy-safety-matrix-768.png` | `b6469b33fa5e822ff573b4de608a1b217c4b6d0e51342de9e60eb022838beae1` | 768×1580 | P/P/P/P/P/P/P |
| webkit | overview | 768×900 | `reviews/visual-finalization/screenshots/webkit/overview-768.png` | `d70f61638ae80581e15508bbd1f15f5d40b27e8556fd44791b1a013d020f75c5` | 768×15514 | P/P/P/P/P/P/P |
| webkit | efficacy | 768×900 | `reviews/visual-finalization/screenshots/webkit/efficacy-768.png` | `abfc52c4fc09db548d0276c40836da9e7c1afdfca7be287d2be83233c20aac18` | 768×2575 | P/P/P/P/P/P/P |
| webkit | safety | 768×900 | `reviews/visual-finalization/screenshots/webkit/safety-768.png` | `400ac32a45cf26fe7e000b1db656d884c01ca0f122586769ee10aeef76df094f` | 768×3905 | P/P/P/P/P/P/P |
| webkit | baseline-overview | 768×900 | `reviews/visual-finalization/screenshots/webkit/baseline-overview-768.png` | `7df0cbac9b33438f4a1447b5166974323be9aa79de66df45c3cbad187d752dc7` | 768×3869 | P/P/P/P/P/P/P |
| webkit | disposition-overview | 768×900 | `reviews/visual-finalization/screenshots/webkit/disposition-overview-768.png` | `9f0236d657ebfd5c03973c24b1802853ab8f3edef1aa4c19242821a24d5dde07` | 768×5738 | P/P/P/P/P/P/P |
| webkit | efficacy-safety-matrix | 768×900 | `reviews/visual-finalization/screenshots/webkit/efficacy-safety-matrix-768.png` | `f822ece3fbafb0c6b86a31ef38414e9b866e5007b51ec591e8522f59c20e99e9` | 768×1633 | P/P/P/P/P/P/P |

All 24 affected 768/1024 records contain:

```json
"unavailable_required_fields": ["全局搜索"]
```

The 12 unaffected 1440 records contain an empty unavailable-field list.

## Responsive Search Alternative

Responsive source behavior was confirmed from the authorized portal assets:

- At widths `768` and `1024`, the default header hides the search input and exposes the visible `菜单` button.
- Clicking `菜单` opens the responsive navigation/search region.
- The test then clicked the now-visible search input, matching the next user action, and confirmed focus.
- Search query: `疗效`.
- Results: `10` on every affected route.
- ArrowDown focus state: verified.
- Escape: results closed and query remained intact.
- Page, console, and request errors: `0` across all 24 responsive-alternative checks.
- Evidence text in each affected record explicitly contains:
  ```text
  点击菜单后使用全局搜索
  ```

Explicit responsive-search screenshots:

| Engine | Width | Relative path | SHA-256 | Image |
|---|---:|---|---|---:|
| chromium | 768 | `reviews/visual-finalization/screenshots/chromium/responsive-search-768.png` | `7b7783beb2b33023c5321a210cb6c5f31c4891cbc7f3b410c3ea3c467eb1e728` | 768×15973 |
| chromium | 1024 | `reviews/visual-finalization/screenshots/chromium/responsive-search-1024.png` | `18d8796a63ad06dfaa155713ecfea68c0ae2ec4cc4e9ec2cf9a785d3a6223495` | 1024×34856 |
| webkit | 768 | `reviews/visual-finalization/screenshots/webkit/responsive-search-768.png` | `6c5db8f925a7d33980463e597d591d59318c08a5f1c295da0561ce1b8aa80e04` | 768×16027 |
| webkit | 1024 | `reviews/visual-finalization/screenshots/webkit/responsive-search-1024.png` | `55e84186dd746d4dd13131290d9b1458b0beb2f0ca26be349e5512354336ecc0` | 1024×34857 |

These four paths and hashes are referenced from every affected record’s `interaction_checks.search` object and from the top-level `responsive_search_artifacts` list.

## Integrity Checks

Metrics artifact:

```text
reviews/visual-finalization/browser-metrics.json
bytes: 347469
sha256: cfe8dc516ff399d888d9d8c1879a63d3b38c2f6fef6f94f95dd7c2a8173ed168
```

Capture metadata:

- Default render records: `36`.
- Total PNGs including four responsive-search evidence images: `40`.
- Aggregate PNG bytes: `46,448,885`.
- Engines: Chromium `149.0.7827.55`, WebKit `26.5`.
- Viewports: `768`, `1024`, `1440`.
- Candidate digest on all records: `f094848b41cf9c66ae8c3ecfb58e0305d5a531f477e6e6cdaa5e05ea3694060e`.
- Existing 24 default screenshot hashes preserved before and after additions.
- New screenshot hashes verified after writing.
- Metrics replacement was staged, parsed, verified, and atomically replaced.
- Temporary metrics file residue: none.

Machine checks:

- Complete engine/page/width matrix: yes.
- Missing recorded screenshots: `0`.
- Screenshot hash mismatches: `0`.
- Duplicate paths: `0`.
- Page-load checks: `36/36`.
- Filtering checks: `36/36`.
- Evidence drawer checks: `36/36`.
- Keyboard Enter/Space checks: `36/36`.
- Focus-visible checks: `36/36`.
- Reduced-motion checks: `36/36`.
- Search checks: `36/36`; 768/1024 passed via the verified menu alternative.
- Page/console/request/runtime errors: `0`.
- Page-level horizontal overflow delta: `0`.
- Non-scroll-container clipped labels: `0`.
- Chart-label overlaps: `0`.
- Unreadable labels: `0`.
- Missing required clinical terms: `0`.
- Engineering/debug labels: `0`.

Visual inspection observations:

- All 12 new 768 default screenshots and all four responsive-search screenshots were inspected in memory and again from disk.
- The 768 layouts use longer stacked cards/tables; chart and table content remains visible.
- Safety heatmaps retain numeric and `不适用` states.
- Baseline charts retain Chinese labels and clinical units.
- Disposition views retain participant-status labels and tables.
- The efficacy–safety matrix retains axes, labels, and the APPOINT-PNH single-arm note.
- No visible clipping, label collision, or unreadable clinical text was observed in the inspected captures.

## Remaining Boundary

- This is browser execution evidence only.
- No formal visual plan, render-evidence JSON, independent verdict, clinical/regulatory acceptance, or delivery-state transition was created.
- No production source, fixture, package index, Trellis record, or old failure candidate was modified.
- The declared fallback identity was `openai-codex / gpt-5.6-luna`; no environment blocker remained.
- Codex retains final visual, clinical, regulatory, candidate-promotion, and delivery authority.
