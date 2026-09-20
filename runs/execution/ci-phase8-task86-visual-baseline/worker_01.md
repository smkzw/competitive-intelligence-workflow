Smoke collection finished (62 shots, 53 hits). I’ll inspect the ledger, drop noisy heuristics if needed, then run the full Chromium/WebKit matrix.Full matrix already landed under `visual-baseline/`. I’ll verify screenshot counts, unique defects, and hashes, then close with the worker report.# Execution Output: ci-phase8-task86-visual-baseline - worker_01

Fallback: Codex primary role was unavailable. This pass was executed by `cursor` / `cursor-grok-4.6` as the declared `pi` fallback for `grok-build` / `grok-4.6`. Playwright Chromium/WebKit collection ran in-process. This worker did not perform Codex final visual, clinical, or regulatory acceptance.

## Boundary And Context Check

- Role: `worker_01` / first-line HTML-PPT visual executor for work item 1 only.
- Read: execution context, Task 8.6 checkpoint hashes, existing collector, smoke ledger, full ledger.
- Authorized writes only: `tools/collect_html_ppt_visual_baseline.py` and Task 8.6 evidence under `docs/acceptance/runs/8.6/`.
- Did not edit `output/html-ppt/`, `assets/html-ppt/`, projection builders, or locked medical JSON.
- Source-of-truth in the execution context is still `TODO`; hashes were bound from Task 8.6 checkpoint and confirmed against current HTML files.

## Work Performed

Implemented reusable collector `tools/collect_html_ppt_visual_baseline.py`:

- Binds A/B/C to Task 8.6 locked SHA-256. Hash mismatch exits 2 and writes `hash-mismatch.json` with no screenshots.
- Walks all 62 slides over Chromium + WebKit and four CSS viewports: 1280×800, 1920×1080, 2048×1024, 1280×720.
- Captures `file://` viewport originals (`device_scale_factor=1`, not element crops).
- Records scale formula, 1280×720 canvas, centering, overflow/clip, remote/console errors, SVG text overlap.
- Writes Chinese markdown ledger + JSON.

Smoke (`bg_2`, Chromium 1280×720) produced 62 shots and 53 hits / 39 unique, dominated by heatmap neighbor `label-spacing`. That near-spacing heuristic was removed from the collector. Overlap detection was kept.

Full matrix is complete: 496 originals, 48 overlap hits, 6 unique defects. Collector exit code 1 means defects exist, not a tool failure.

## Artifacts And Evidence

| Artifact | Role |
|---|---|
| `tools/collect_html_ppt_visual_baseline.py` | Reusable collector |
| `docs/acceptance/runs/8.6/visual-baseline/visual-baseline-ledger.md` | Chinese ledger |
| `docs/acceptance/runs/8.6/visual-baseline/visual-baseline-ledger.json` | Machine ledger |
| `docs/acceptance/runs/8.6/visual-baseline/screenshots/{chromium,webkit}/{viewport}/*.png` | 496 originals (289,354,085 bytes ≈ 276 MiB) |
| `docs/acceptance/runs/8.6/visual-baseline-smoke/` | Intermediate Chromium-only smoke pack |

Bound hashes (match):

- A `adcf8487aa85996d0d4886d7801a16a544f2b703cac5a331d4a7a7af085eb2e4` (20)
- B `087d04b0aa1ddb0da26c5370fcf26e8bb328efc4705136194bbe0ecdb5740b1d` (24)
- C `fd2d47565bfdb1b12f6405c62ed53f9762eac67c92175302a5a6eba8d3064113` (18)

Automatic unique defects (medium, SVG overlap only; no blocker/high):

- `a-efficacy`: `611` × `（SSGJ-611）`; `（SSGJ-611）` × `第16周`; `乐德奇拜单抗` × `（Rademikibart / SIM0718）`; `（Rademikibart / SIM0718）` × `第16周`
- `a-efficacy-3`: `64.0` × `治疗组`
- `a-matrix-2`: `曲罗芦单抗` × `来布利珠单抗` (matches 8.5 handoff)

`b-efficacy` and `c-endpoints` did not auto-alarm; originals exist for human review.

Evidence from sampled cover pages: zero remote/page/console/overflow/clip/scale/canvas failures. Logical canvas 1280×720. Scale matched `min(vw/1280, vh/720)` (`1`, `1.5`, `1.422…`, `1`).

## Commands And Observations

1. Smoke `bg_2`: `uv run python tools/collect_html_ppt_visual_baseline.py --browsers chromium --viewports 1280x720 --output-dir docs/acceptance/runs/8.6/visual-baseline-smoke` — 61.67s; `screenshots=62 defect_hits=53 unique=39`; exit 1 because defects exist. Observation: heatmap neighbor spacing flooded the ledger.
2. Collector JS no longer contains `label-spacing`.
3. Full run already recorded at `2026-08-31T04:59:03.971995+00:00`: 496 PNG on disk matching JSON; 62 Chromium 1920×1080 index rows; unique defects 6.

## Blockers Or Missing Environment

None for this collector. Playwright Chromium and WebKit were already available; no packages were installed.

Limitation: viewports are Playwright CSS sizes, not an OS-native maximized window (`viewport=None`). That remains a Task 8.6 gap for Codex / worker_03.

## Rerun Requests Or Next Step

```text
uv run python tools/collect_html_ppt_visual_baseline.py
```

Ask Codex:

1. Track ~276 MiB of PNGs in git, or keep only ledger + watch-page originals?
2. Delete `docs/acceptance/runs/8.6/visual-baseline-smoke/`?
3. Should a later pass add OS-maximized (`viewport=None`) originals, or is the CSS 1280×800 / 1920×1080 matrix enough?

Worker_02 should use these originals for page-level readability. This worker does not accept the deck.
