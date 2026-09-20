# Conference Participant Output: ci-phase8-task84-runtime-visual-review - visual_single_object

## Boundary Check

- Read-only pass. No file written or modified; runner-managed report path untouched.
- Read scope limited to the source packet: `assets/html-ppt/` hashes (shasum only), `tests/acceptance/test_html_ppt_runtime_smoke.py` (grep only), `docs/acceptance/runs/8.4/` (all four files + eight PNGs). No production paths, no network, no other participant outputs.
- No acceptance claim made; Codex remains final authority. This is an advisory independent review.

## Independent Work Product

I re-opened all eight raw screenshots and cross-checked them against the ledger, evidence md, and smoke-test assertions.

**Per-screenshot observations (evidence):**

| Screenshot | Observed content | Verdict |
|---|---|---|
| `*-1280x720-slide-2.png` (both browsers) | Slide 2「主要疗效」, subtitle, offline bar chart （竞品甲/乙/丙）, page number `2 / 3` bottom-right, thin dark progress bar at bottom edge. Canvas fills viewport exactly (scale=1 at native 1280×720). Chromium/WebKit visually identical. | No blocker |
| `*-1280x720-notes.png` (both) | Same slide with 逐字稿 drawer open at bottom; drawer header「逐字稿」+ body「本页说明主要终点及对照组效应，提醒跨试验比较需结合研究差异理解。」; drawer overlays canvas without displacing it. Both browsers identical. | No blocker |
| `*-1920x1080-presenter.png` (both) | Presenter grid: 当前页「竞品格局 1/3」, 下一页「主要疗效 2/3」with chart rendered inside preview iframe (scaled, not clipped — G3 fix visible), 逐字稿「本页说明竞品格局及关键证据…」, 计时 `00:00`, 页码 `1 / 3` +「第1页，共3页」, buttons 上一页/下一页/重新计时. Chinese presenter chrome confirmed. | No blocker, but see defect D1 |
| `*-echarts-svg.png` (both) | Full-viewport ECharts bar chart「主要终点变化值」, axes 0–6, three labeled bars; standalone chart fixture renders identically in both engines. | No blocker |

**Hash verification:** `runtime.js` `9f8306a2…`, `runtime.css` `09df452d…`, `echarts.min.js` `b66b25ae…` all match the ledger exactly — the reviewed binaries are the recorded ones.

**Test cross-check:** the smoke test numerically asserts the properties screenshots can only imply: `--deck-scale` unrounded `min(vw/1280, vh/720)`, center error ≤0.5 px on both axes, slide-number `2 / 3`, hash `#/2`, progress width 66.6%, `#efficacy-chart svg` present with zero `canvas`, drawer open/close, presenter titles/script/page-detail/timer/buttons, `file:` protocol with empty remote/page/console error audits. Coverage is real, not ceremonial.

**Fixture-vs-master discipline:** the fixture is plain white with system default blue bars. I do not flag its minimal styling as a defect — Kangzhe master/FX is explicitly Task 8.5, maximized-window visuals Task 8.6. Nothing in the runtime chrome (page numbers, drawer, presenter grid, progress bar) pre-judges the visual master.

## Evidence And Assumptions

- **Evidence:** eight PNGs re-viewed; three SHA-256s recomputed and matched; ledger/evidence/verdict/gap-audit read; smoke-test assertions grepped; `sips` pixel dims read for all PNGs.
- **Assumption:** presenter timer shown as `00:00` is the post-reset/fresh state; the test asserts `00:00` statically, so timer *ticking* is not visually proven by these screenshots (acceptable — the contract is presence + reset, and R-key reset is test-covered).
- **Assumption:** BroadcastChannel two-way sync and `?preview=` freeze are asserted in the ledger and gap audit (G5/G9 patches); I did not re-execute the sync dance — I treated ledger + test structure as sufficient for this read-only pass.

## Risks, Gaps, And Verification Needs

**D1 (highest impact — evidence-label mismatch, not runtime blocker):** files named `chromium-1920x1080-presenter.png` / `webkit-1920x1080-presenter.png` are actually **1440×900 pixels** (sips, both browsers). Either the capture viewport was 1440×900 (likely a default headless window at DPR 1), or DPR naming drifted. Impact: the ledger claims presenter-view evidence at 1920×1080; the artifact does not prove that viewport for the presenter chrome. The audience-page scale formula is numerically tested at 1920×1080, so the runtime contract still stands — but the *visual* presenter evidence at that viewport does not exist. **Proposed remedy:** rename the files to their true dims or recapture presenter at 1920×1080 and update the ledger hashes. Bounded question for Codex: does the 8.4 contract require presenter *visual* evidence at 1920×1080, or is numeric scale coverage + 1440×900 presenter screenshot sufficient? Provisional safe path: treat as evidence hygiene issue for Codex adjudication, not a Task 8.4 blocker.

**D2 (minor):** no screenshot demonstrates dual-axis centering at a non-16:9 viewport (2048×1024 → horizontal letterbox). Centering is only numerically asserted (centerError ≤0.5 px). A letterbox screenshot would make the "双轴居中" claim visually auditable; currently it rests on math assertions. Remedy: add one 2048×1024 audience screenshot in 8.6 sweep rather than reopening 8.4.

**D3 (cosmetic, both browsers identical → chrome design, not defect):** presenter 下一页 column shows the slide-2 preview stacked above a black「演示结束」placeholder in the same column. Consistent across engines; likely intentional end-of-deck indicator. Flag only so nobody mistakes it for a render bug in 8.5 theming.

**D4 (residual, by design):** T/A/O features removed; FX layer absent. Correct for 8.4 scope per gap audit G10/G11/G13.

## Recommended Next Step

Codex adjudicates D1 (pixel-dim vs filename vs ledger claim) — rename or recapture — then this conference can close with no runtime blocker: fixed canvas, dual-axis centering (numeric), 逐字稿 drawer, presenter current/next/page/timer, and offline ECharts SVG all verified consistent across Chromium and WebKit. Defer D2 letterbox screenshot and all visual-master/FX/maximized-window checks to Tasks 8.5/8.6 as planned.
