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

- `docs/acceptance/runs/8.4/screenshots/chromium-1280x720-slide-2.png` `bdda1b1c023b` (28065 bytes)
- `docs/acceptance/runs/8.4/screenshots/chromium-1280x720-notes.png` `188d73e1cd98` (41037 bytes)
- `docs/acceptance/runs/8.4/screenshots/chromium-1440x900-presenter.png` `5d42c7441fca` (60097 bytes)
- `docs/acceptance/runs/8.4/screenshots/chromium-echarts-svg.png` `0369154a1313` (10340 bytes)
- `docs/acceptance/runs/8.4/screenshots/webkit-1280x720-slide-2.png` `0c3748da69ad` (46420 bytes)
- `docs/acceptance/runs/8.4/screenshots/webkit-1280x720-notes.png` `b8d2907324b8` (60969 bytes)
- `docs/acceptance/runs/8.4/screenshots/webkit-1440x900-presenter.png` `d418f672fef3` (84618 bytes)
- `docs/acceptance/runs/8.4/screenshots/webkit-echarts-svg.png` `9d2bf24286c7` (26155 bytes)

## Residual

- Kangzhe visual master / FX injection is Task 8.5.
- Native maximized-window visual pass is Task 8.6.

