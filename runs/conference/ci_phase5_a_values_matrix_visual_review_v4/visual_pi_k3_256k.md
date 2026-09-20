先读取会议上下文和主场计划，再按医学经理视角独立验收最终 HTML 报告。已拿到验收范围。接下来打开最终 HTML 产物、既有截图和设计规范，再在多视口下实检。设计规范路径不存在。接下来读 HTML/CSS 结构，并对照已有截图，随后在四个视口实渲染。已有 1024 截图只露出两列。接着读矩阵布局 CSS，并打开其余截图与页面源码。四个维度已确认是上下两块、每块两列。接着核 CSS 断点，并用浏览器在 768/1440 实测溢出与交互。1280 截图第一块像是三列、第二块只剩鼻咽炎。继续读渲染逻辑，并启动真实视口测量。代码在 1000–1250px 容器宽时会切成 3+1 列。接下来用 Playwright 在四个视口实测溢出、分块和筛选交互。safety.html 很大，测量脚本还在跑。等它结束后再读指标和截图。1440 仍是 3+1 分块，宿主宽只有 1100。接着看实渲染截图，并测筛选交互与表头遮挡。768 明细表中文被拆字，1440 热图是 3+1。接下来实测筛选是否同步图表，并核对 1024 表格可读性。筛选交互和 768 表格拆字已经坐实。正在整理独立验收结论，不改文件、不替代 Codex 终验。# Conference Participant Output: ci_phase5_a_values_matrix_visual_review_v4 - visual_pi_k3_256k

## Boundary Check

- Role: `visual_pi_k3_256k` / Grok Build `grok-4.6`. Advisory visual pass only. Codex remains final authority.
- Worked only in the runner-bound workspace. Did not read production paths, other participant outputs, home AGENTS.md, or SOUL.md.
- Did not edit source, artifacts, or screenshots. Did not write `runs/conference/.../visual_pi_k3_256k.md` or sibling files.
- Did not claim final visual/clinical/regulatory acceptance. Chromium-only live render; WebKit not re-run in this pass.
- Tools used: filesystem read of the assigned packet; Chromium Playwright measurements and viewport screenshots written only to `/tmp/ci-visual-v4/` (scratch, not a conference sibling).

## Independent Work Product

Independent visual audit of the final A-class atopic dermatitis HTML report from a senior clinical-trial medical-manager reading path. Pages opened: `overview.html`, `safety.html`, `efficacy.html`. Viewports: 768 / 1024 / 1280 / 1440 CSS px, Chromium, height 900.

### Highest-impact defect (do not treat Codex’s 2×2 check as closed)

At 1280 and 1440, the default safety heatmap is **3+1, not 2+2 and not 4-across**. The first screen of the safety heatmap shows only 任何TEAE / 任何SAE / 预先界定AESI. 鼻咽炎 is a second 38-row block below the full product list. A medical manager who stops at the “complete” looking first grid never sees the fourth default dimension.

**Observation (measured, Chromium):**

| Viewport | Chart host width | Blocks | First-block headers | Second-block headers | Page `scrollWidth-clientWidth` (overview/safety) |
|---|---|---|---|---|---|
| 768 | 668 | 2 | 任何TEAE, 任何SAE | 预先界定AESI, 鼻咽炎 | 0 |
| 1024 | 924 | 2 | 任何TEAE, 任何SAE | 预先界定AESI, 鼻咽炎 | 0 |
| 1280 | 1100 | 2 | 任何TEAE, 任何SAE, 预先界定AESI | 鼻咽炎 | 0 |
| 1440 | 1100 | 2 | same 3-col | 鼻咽炎 only | 0 |

Root cause in code, not in “the screenshot happened to crop”:

- `safetyTermsPerBlock()` uses **host.clientWidth**, returning 2 if `<1000`, 3 if `<1250`, 4 if `≥1250` (`assets/report-a.js`).
- `.portal-main { max-width: 1200px }` wins over `.kz-a-main { max-width: 1440px }`, so at 1440 the chart host is still **1100 px**.
- Four-across is therefore **dead**. 1440 never reaches the 1250 host threshold. 1280/1440 always emit a leftover single-column 鼻咽炎 grid.

This **contradicts** the main-venue checklist item already marked done: “首页和安全性详情页默认均有4个安全性维度，按两块每块2列排布.” Packet screenshots `overview-1280.png` / `safety-1280.png` already show 3+1; live 1440 repeats it.

**Inference:** “默认完整显示四个安全性维度” as a medical-manager criterion means the four default column headers are co-visible in the heatmap module without scrolling through 38 rows. 2+2 at 768/1024 is an acceptable wrap. 3+1 at 1280/1440 is not: the first grid looks finished, AESI is almost all 未公开, and the only densely populated fourth dimension is hidden.

**Recommendation (remediation, not implemented):**

1. Never emit a 3+1 remainder. Use 2 until the host can actually fit 4.
2. Either raise `.portal-main` to 1440 so 1440 can host four columns, or drop the 4-column threshold to ≤1100.
3. Provisional safe path until Codex decides: treat 1280/1440 visual closure as **not passed**.

### 768 safety detail table: Chinese is broken to avoid horizontal scroll

**Observation:** Overview and safety pages have **no page-level horizontal overflow** at 768–1440 (Chromium). The 8-column safety table uses `overflow-x: visible` plus `overflow-wrap: anywhere`. At 768, 发生率/人数 cells are ~53 px wide. Visual capture of `safety-768-table-viewport.png` shows:

- 未公开 → 未公 / 开
- 特别关注不良事件 → 特别关注不 / 良事件
- 治疗期间不良事件 → 治疗期间不 / 良事件
- Rocatinlimab → Rocatin / limab; Tezepelumab → Tezepel / umab
- Sticky thead sits under the 68 px header (`--header-h: 64px` vs measured header 68 px, 4 px overlap). First data row is clipped (leading “mab”).

At 1024 the same table is usable: 未公开 stays intact; 特别关注不良事件 stays one line; product names wrap at 单抗, which is acceptable.

**Inference:** The no-horizontal-drag rule was met by destroying CJK readability at tablet width. A medical manager cannot scan 发生率 or 未公开 at 768.

**Recommendation:** Do not wrap status/rate cells with `anywhere`. Prefer a sticky product column plus intentional `overflow-x: auto` on the table, or hide 试验/人数 below 900 px. A labeled inner table scroll is better than 未公/开.

### Chart-first, numeric hierarchy, unpublished vs window (pass, with caveats)

**Observation:**

- Homepage module order: 竞争格局 → 主要疗效 → 关键安全性 → 疗效与安全性位置. Safety page: filters → 热图 → 明细表. Matches “图表优先.”
- Heatmap: bold rate, smaller observation window under the number, gray 未公开, in-column color only. Footnote states 治疗组/对照组 and that gray means 未公开. Logo `alt="康哲药业"` is 121×25 and visible at all four widths.
- Efficacy bars: 橙色治疗组 / 蓝色对照组 note is **below** the last row at all four widths (`legendOverlapsLastRow: false`). Last labeled product APG777 is not covered.
- Heatmap event labels stick at `top: 68` with **0 px overlap** with the site header (768 check). Table thead does overlap by 4 px.

**Caveats (inference, not science re-review):** 预先界定AESI is almost entirely 未公开 in the default view, so at 1280/1440 the first screen is two useful columns plus a gray dummy. 克立硼罗 TEAE cell window text includes both “AE: … SAE: …”, which mixes dimensions inside one cell.

### Filter / table interaction

**Observation (safety, 1280, live clicks):**

- Default digest: 38 products; terms `any_teae | any_sae | raw:预先界定aesi | nasopharyngitis`. Table “第 1/205 页｜当前筛选 10228 条”.
- Product 度普利尤单抗: heatmap → 1 row; table → 103 rows. Fourth term **changes** 鼻咽炎 → 特应性皮炎.
- Add 乌帕替尼 + 对照组: note becomes 当前组别：对照组; chips show 对照组 pressed; table 453 rows. Reset restores 38 / 鼻咽炎.
- Category 常见不良事件: heatmap collapses to **only 鼻咽炎**; table still 6124 rows (all common AEs). Chart and table are not the same slice.
- Default 治疗组 is applied in data (`当前组别：治疗组`) but **neither 治疗组 nor 对照组 chip is pressed** until the user clicks. Medical manager cannot see the active arm from the chips.

**Inference:** Product and arm filters do sync heatmap + table. Category filter does not: the heatmap is still a 4-default-term summary (or 1 leftover term), while the table is the full category. The fourth default common AE is coverage-ranked and unstable under product filters, so “一项常见AE” is not a fixed comparison column.

**Recommendation:** Either (a) make category filter drive heatmap terms in that category, or (b) constrain the table to the terms actually drawn. Mark default 治疗组 as `aria-pressed="true"`. Freeze the default four keys when the user has not picked an event.

### What passes from this Chromium pass

- Overview and safety: no page-level horizontal scroll at 768/1024/1280/1440.
- Default unfiltered model contains all four required dimensions (它们在 DOM 里，不只是两列).
- Logo, title, 1440 full nav, ≤1320 hamburger: no collision that blocks entry.
- Efficacy chart legend does not cover the last bar row.
- Heatmap sticky headers do not collide with page nav.
- 1024 safety table is readable enough to use.

## Evidence And Assumptions

**Evidence**

- Sources: `.artifacts/a-values-matrix-fix-final-v4/reports/A/v1/html/{overview,safety,efficacy}.html`, `assets/portal.css`, `assets/report-a.js`; packet screenshots under `reviews/ci_phase5_a_values_matrix_fix_screenshots/final-v4/`; live Chromium metrics `/tmp/ci-visual-v4/metrics.json`.
- `docs/design/kangzhe-design-spec.md` is absent (`docs/design` does not exist). Visual review used page consistency and the stated medical-manager criteria, not that file.
- `safetyTermsPerBlock` and `.portal-main { max-width: 1200px }` as cited above.
- Live filter digest strings and page-status text as recorded in the Independent Work Product.

**Assumptions**

- “默认完整显示四个安全性维度” is judged from the heatmap module’s first viewport after the module is in view, not “exists somewhere after 2000 px of product rows.”
- “无横向拖动” is page-level plus heatmap-level; an inner table gutter scroll would still be a defect if unlabeled, but is preferable to CJK character splitting.
- Efficacy is in scope for chart order, legend, and table interaction, not as a second scientific review.
- Default 治疗组 with unpressed chips is unintentional, not a hidden “all arms” mode (heatmap footnote says 治疗组).

**Uncertainty**

- WebKit/Safari not executed here. Codex checklist claims WebKit no-overflow; this pass cannot confirm or deny it.
- Whether 3+1 was an intentional wide-layout choice. Behavior plus 1200 px cap makes it look like a threshold bug, not a design.
- Whether 特应性皮炎 as a “常见AE” after filtering to 度普利尤单抗 is scientifically intended (worsening of AD) or a term-ranking accident. Out of visual-only scope; flagged for Codex.
- Event filter still contains English source terms (e.g. SKIN BACTERIAL INFECTION). Not fully walked beyond 鼻咽炎.
- 768 first-viewport of **homepage** does not include the safety heatmap at all (it sits under landscape + efficacy). That is information architecture, not a matrix overflow bug.

## Risks, Gaps, And Verification Needs

**Risks if Codex accepts as-is**

- Medical managers at 1280/1440 will brief from a 3-column heatmap and miss 鼻咽炎, the only well-populated fourth dimension.
- 768 table is not presentation-ready for a tablet/projection of the 明细.
- Category filter can be read as “show common AEs” but the heatmap shows one term while the table has 6000+ rows.

**Gaps this pass did not close**

- WebKit at the four widths.
- Sticky thead vs nav after opening the 菜单 drawer (header height may grow).
- Full event-filter 598-item usability and English-term density.
- PDF/PPT (out of scope).
- B/C-class reports (out of scope).

**Verification Codex still owns**

1. Re-measure 1280/1440: count heatmap blocks and whether 鼻咽炎 is in the first heatmap viewport. If 3+1 remains, do not keep the “两块每块2列” checkbox.
2. Open `safety.html` at 768 and read 未公开 / 不良事件 in the first table page. Accept or reject the wrap-vs-scroll trade.
3. Click 常见不良事件 and compare heatmap term set vs table row set.
4. Optional WebKit repeat of overflow only; not a substitute for the 3+1 question.

**Objections to the current main-venue plan**

- The plan treats 768/1024/1280/1440 as one “no overflow, four dimensions, 2×2” bundle. Overflow and dimension **presence** can pass while dimension **co-visibility** and CJK table readability fail. Those must be scored separately.
- Packet screenshots at 1024/1280 are insufficient for 768 table wrapping and 1440 3+1; both are now observed live.

**Decision points for Codex**

1. Is 3+1 at 1280/1440 a fail against “默认完整显示四个安全性维度”? This participant: **yes**.
2. Is 768 `overflow-wrap: anywhere` on the 8-column table an accepted anti-scroll trade? This participant: **no**.
3. Is coverage-ranked fourth term allowed to change under product filter? Needs an explicit product rule.

**Bounded questions**

1. For visual closure, must all four default headers be in the same heatmap viewport (2×2 or 4-across), or is “present after vertical scroll through block 1” enough?
2. If (1) is co-visibility: authorize a layout-only fix (no 3-col remainder; make 4-across reachable at 1440) without reopening scientific data?
3. At 768, which is the accepted table behavior: inner horizontal scroll with sticky 产品, or stacked/hidden columns? Character-level wrap should not remain the default.

**Provisional path if Codex cannot answer in-session:** do not grant visual acceptance of final-v4. Keep the artifact, record 3+1 + 768 CJK wrap as open visual defects, and do not ship this HTML as tablet/desktop-complete.

## Recommended Next Step

Codex should treat this as a **visual fail on two concrete points**, not a pending opinion:

1. Eliminate 3+1 (force 2 until host width truly fits 4; align `portal-main` max-width with the 4-column threshold).
2. Repair 768 safety-table CJK wrapping (stop `overflow-wrap: anywhere` on 未公开/发生率/维度).

Re-open `safety.html` at 768 and 1440 after that change; bind acceptance to the new run, not to file existence or the previous 1024/1280 packet screenshots. This participant does not authorize those edits and does not replace Codex final acceptance.
