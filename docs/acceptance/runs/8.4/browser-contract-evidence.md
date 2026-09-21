# Task 8.4 HTML-PPT browser contract evidence

Date: 2026-08-31
Worker: `worker_03` (cursor / grok-4.6 fallback of grok-build)
Status: **not acceptance**. Codex remains the final authority for visual, PPT, clinical, and regulatory decisions.

## Contract covered

- Chromium and WebKit against 1280×720, 1600×900, 1920×1080, 2048×1024.
- Maximized-window *semantics*: `--deck-scale` equals unrounded `min(clientWidth/1280, clientHeight/720)` with logical canvas 1280×720. Task 8.6 still owns native maximized-window visual acceptance.
- `file://` protocol, zero `http(s)/ws(s)` requests, no page or console errors.
- Audience ↔ presenter two-way sync, notes drawer, timer reset, `?preview=` freeze.
- Offline ECharts SVG renderer (no canvas) in the runtime fixture and the standalone chart fixture.

## Recorded hashes

- `assets/html-ppt/runtime.js` `affadf9e344ec9da62cdd27942a41218983d2cb88a377eca540b7da622a990f7`
- `assets/html-ppt/runtime.css` `09df452da708ac80a9660bb49ff8603cfac85aec7e607852c99ca09a209517d0`
- `assets/third-party/echarts/echarts.min.js` `b66b25aeb4df84e33199dc21694014d336d222cbd9deb0e5a7c14bd6aa0d0fd0`
- Ledger `docs/acceptance/runs/8.4/browser-contract-ledger.json`

## Screenshots

- `docs/acceptance/runs/8.4/screenshots/chromium-1280x720-slide-2.png` `b80edb1c34ae` (28401 bytes)
- `docs/acceptance/runs/8.4/screenshots/chromium-1280x720-notes.png` `8a5aab66bcac` (41689 bytes)
- `docs/acceptance/runs/8.4/screenshots/chromium-1440x900-presenter.png` `85643c193a2e` (61451 bytes)
- `docs/acceptance/runs/8.4/screenshots/chromium-echarts-svg.png` `140f4c78ba48` (10350 bytes)
- `docs/acceptance/runs/8.4/screenshots/webkit-1280x720-slide-2.png` `b750a39a2300` (47025 bytes)
- `docs/acceptance/runs/8.4/screenshots/webkit-1280x720-notes.png` `fc0ba9467b25` (61886 bytes)
- `docs/acceptance/runs/8.4/screenshots/webkit-1440x900-presenter.png` `ed92625b3d69` (87416 bytes)
- `docs/acceptance/runs/8.4/screenshots/webkit-echarts-svg.png` `4e7cdf74abf0` (26089 bytes)

## Residual

- Kangzhe visual master / FX injection is Task 8.5.
- Native maximized-window visual pass is Task 8.6.

