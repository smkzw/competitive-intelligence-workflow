# Task 8.4 HTML-PPT runtime gap audit

Date: 2026-08-31  
Worker: `worker_01` (cursor / grok-4.6 fallback of grok-build)  
Scope: candidate `assets/html-ppt/` vs `contracts/kangzhe/design_specs/track_htmlppt.md` §0.1–0.2 / §14.2–14.4 / §14.8 and peer skill `/Users/smkzw/.codex/skills/html-ppt/assets/runtime.js`.  
Not acceptance. Task 8.5 visual narrative, portal/PDF reuse, and T/A/O features remain out of scope.

## Sources read

| Source | Role | Observation |
| --- | --- | --- |
| `contracts/kangzhe/design_specs/track_htmlppt.md` §0.1, §0.2, §14.2–14.4, §14.8–14.9 | Project contract | 1280×720 logical canvas; `--deck-scale` on `:root`; `s=min(vw/1280,vh/720)` unrounded; `#/N` only; `.deck > .slide`; per-slide `.slide-number`; no generic theme |
| `contracts/kangzhe/design_specs/htmlppt_fx.md` | FX after runtime | Example path `assets/runtime.js`; freeze on `?preview=` |
| `assets/html-ppt/{runtime.js,runtime.css,manifest.json,LICENSE}` | Project candidate | MIT derivative of skill commit `f3a8435` |
| Skill `runtime.js` SHA-256 `d7b066a96b99fcf5c9e15b593283a57a3d43ac2bcf795d172adc7f3ba0844f79` | Upstream interaction reference (read-only) | Matches `manifest.source_runtime_sha256` |
| `tests/fixtures/html-ppt-runtime/index.html` | Runtime-only fixture | Isolated; no portal/PDF/kangzhe visual master |
| `tests/acceptance/test_html_ppt_runtime_smoke.py` | Candidate tests | Worker 03 owns expansion |

## Kept from the peer skill (intentionally)

- Keyboard: arrows, space, PageUp/Down, Home/End, F, N, S, R, Escape
- `#/N` 1-based hash
- `?preview=N` locked single-slide mode
- BroadcastChannel audience ↔ presenter
- Presenter: current / next / notes / timer
- MIT LICENSE + commit + hashes in `manifest.json`
- Removed T / A / O (theme, demo animation, overview clone)

## Gaps found (before patch)

| ID | Severity | Evidence | Patch in this worker? |
| --- | --- | --- | --- |
| G1 | High | §14.3 writes `--deck-scale` on `document.documentElement` and uses `clientWidth/Height` + `visualViewport` + rAF. Candidate used `window.innerWidth/Height` on `.deck` only, no visualViewport. | Yes |
| G2 | High | §14.3: initialize every `.slide-number`. Preview early-return skipped `updatePerSlideNumbers()`. Skill only updates first `.slide-number`. | Yes |
| G3 | High | Skill presenter iframes are 1920×1080. Project canvas is 1280×720. Candidate preview used `transform:none` with iframe `width:100%`, so speaker preview clipped instead of scaling the 1280 canvas. | Yes: iframe 1280×720 + `min(host/1280, host/720)` |
| G4 | Medium | §14.4 skeleton already has `.progress-bar`. Candidate always appended a second `.deck-progress`. | Yes: reuse `.deck-progress, .progress-bar` |
| G5 | Medium | Preview `preview-goto` expected `index`; skill posts `idx`. Dual-window sync used mismatched `go`/`slide` payloads. | Yes: accept `index ?? idx` |
| G6 | Medium | `showSlide` always `replaceState` hash; §14.3 requires `hashchange` path `writeHash=false`. | Yes |
| G7 | Medium | Notes only `aside.notes`; contract/skill also `.notes` / `.speaker-notes`. | Yes |
| G8 | Low | Print hide list in §14.2 uses `.progress-bar,.notes-overlay`. Candidate used only derived class names. | Yes: dual class names |
| G9 | Low | Presenter reloaded iframe `src` every page change (flicker). Skill loads once + `postMessage`. | Yes: load once + `preview-goto` |
| G10 | Info | Design examples say `assets/runtime.js`; project keeps `assets/html-ppt/runtime.js`. Delivery copy/alias is Task 8.5 packaging, not 8.4. | No write to design_specs |
| G11 | Info | FX `gx_fx.css/js` not loaded in 8.4 fixture. Required for official decks in 8.5, forbidden as visual master here. | No |
| G12 | Info | Smoke test viewports 1600×900 and 2048×1024; contract also 1280×720 and 1920×1080. | Worker 03 |
| G13 | Residual | Skill magnetic cards / localStorage layout not ported. Task 8.4 Chinese presenter grid is the project contract; magnetic theme chrome would fight Kangzhe. | Intentional |

## Patches applied

- `assets/html-ppt/runtime.js`: root scale, client viewport, rAF, visualViewport, fonts.ready, preview numbers, hash write flag, notes selectors, progress reuse, 1280 presenter iframe scale, preview-goto, dual message keys, webkit fullscreen prefix.
- `assets/html-ppt/runtime.css`: global `box-sizing` (same as §14.2), print/preview hide aliases, comment that `.tpl-kangzhe .deck` may override transform.
- `assets/html-ppt/manifest.json`: derived SHA-256 updated after patch.

Post-patch hashes:

- `runtime.js` `8f462234fc64a24d8f6b65ed80a1b1a73b5caae5dbe12fd0030c98db4e588c01`
- `runtime.css` `711ec575ef5cb535012c00ab252969a9a2e6536f543b6827b15fb31eed29335c`

## Explicit non-goals left for sibling workers

- Worker 02: remaining runtime contract completeness (audience/presenter live sync proof, timer R from both windows, maximized-window semantics).
- Worker 03: Chromium/WebKit matrix including 1280×720 and 1920×1080, `file://` zero-remote, ECharts SVG evidence under `docs/acceptance/runs/8.4/`.
- Codex: visual/clinical/regulatory acceptance.

## Assumptions

- Setting `--deck-scale` on both `:root` and `.deck` is compatible with later `.tpl-kangzhe .deck { transform: scale(var(--deck-scale, 1)) }`.
- Presenter iframe scale is a chrome transform, not a second scale on `.deck` (preview mode keeps deck `transform: none`).
