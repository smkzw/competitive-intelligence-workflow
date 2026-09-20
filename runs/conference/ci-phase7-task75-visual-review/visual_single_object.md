The packet names freeze `bcf4fb22…`. I’ll re-hash both trees, then check only the axis label, dossier title, filter copy, and no-regression items.# Conference Participant Output: ci-phase7-task75-visual-review - visual_single_object

## Boundary Check

- Role: `visual_single_object` (Pi / cursor-grok-4.6). Advisory only; no production edits; no clinical/regulatory/final visual acceptance.
- This pass inspects **only** digest `bcf4fb223bea61c282684e80d2bae8c1906ecc7b2cf9d500970ee385da4df058`. It does **not** reuse conclusions from `4a5c4825`, `b2b89805`, `ee31bcdb`, `51bf3506`, `c4cdae0a`, `47bb95b2`, `51b793bd`, or `2c47e67c` as current truth.
- Recalculated from `reviews/ci-phase7-task75-report-c-portal/site/` with `find . -type f -print0 | sort -z | xargs -0 shasum -a 256 | shasum -a 256` → `bcf4fb223bea61c282684e80d2bae8c1906ecc7b2cf9d500970ee385da4df058`. **Match.** Same digest on `final-candidate/site/`. **0 byte diffs.** 27 files. No `assets/charts.js`. `report-c.js` 23221 bytes.
- Scope this round: axis short name, dossier `NCT编号 试验档案` title, dossier filter copy vs “模块级”, and no-regression of dose wrap / 疗程 / 1024 overflow. Science completeness is **not** expanded.
- Evidence: frozen HTML/`report-c.js`; live Chromium 1024×900 on `127.0.0.1:18774`; current 2026-08-31 00:47 stills `chromium_treatment-arms_1024.png`, `chromium_overview_1024.png`, `chromium_nct02260986_1280.png`. Did not read other conference participant outputs.
- **Excluded:** `chromium_overview_1280_chart_scrolled.png` / `chromium_overview_1280_filter_collapsed.png` (historical 22:34/22:35 pair).
- No Trellis task this round (conference artifact only; no edit authorization).

## Independent Work Product

### Conference opinion (not Codex final acceptance)

**通过。** The named closure holds on digest `bcf4fb22`. Chart axes show `奈莫利珠单抗研究` with **no ellipsis**. Per-trial titles are `NCT编号 试验档案`. Dossier filter copy is Chinese user language; `模块级` is absent from all HTML. Prior pass items (unsplit `250 mg`/`300 mg`, complete 频次/负荷/疗程, 1024 no horizontal drag) did **not** regress. No new high/critical visual, Chinese-copy, or interaction blocker. Codex remains the final visual/clinical/regulatory authority.

### Named checks

**1. Long trial name on chart axes — Pass.**

- `trialLabel()` special-cases names containing `奈莫利珠单抗` to **`奈莫利珠单抗研究`** before the `>12` ellipsis fallback. That short name is 7 characters, so it does not hit `…`.
- Live grouping and 首页 canvases at 1024: axis text `NCT03985943` + **`奈莫利珠单抗研究`**. `ellipsis=[]` on both pages.
- Current Chromium `treatment-arms_1024.png` / `overview_1024.png` (00:47) quote the same untruncated label.

**2. Per-trial title `NCT编号 试验档案` — Pass.**

Live and frozen HTML:

| File | `h1` / `<title>` prefix |
|---|---|
| `trials/nct02260986.html` | `NCT02260986 试验档案` |
| `trials/nct03985943.html` | `NCT03985943 试验档案` |
| `trials/nct04178967.html` | `NCT04178967 试验档案` |
| `trials/nct05149313.html` | `NCT05149313 试验档案` |

Concatenated `NCT02260986试验档案` count is **0**. Current dossier 1280 PNG shows the spaced `h1`. Chart title on that page remains the correct single-trial `本试验核心设计`.

**3. Per-trial filter copy is Chinese user language, not “模块级” — Pass.**

- `模块级` count across all 16 HTML files: **0**. `data-filter-scope="module"` remains an attribute only, not user-visible.
- Visible dossier chrome: `筛选条件` / `未设置筛选` / `设计要素` / `图表及明细 · 可多选` / `点击数值或表格单元格查看数据依据。` / lead `本页保留该试验全部可定位设计事实，可下钻到来源版本与原文。`
- Comparison pages keep `快速筛选` / `进一步筛选` / `快速筛选作用于整页；以下选项可进一步限定图表和明细。`

**4. No regression of dose wrap, 疗程, or 1024 overflow — Pass.**

Live grouping at 1024: overflowX=**0**; table `sw=cw=1000`; `split=[]`.

| Check | Live canvas |
|---|---|
| `300 mg` unsplit | `度普利尤单抗 300 mg` / `剂量300 mg、600 mg` |
| `250 mg` unsplit | `剂量500 mg、250 mg` / `剂量250 mg；每2周1次` |
| 每2周1次 / 含负荷剂量 | present |
| 第1周至第51周 / 基线至第52周 | present |
| `Lebrikizumab 匹配安慰剂` | spaced, intact |

首页 overflowX=0 with the same period phrases. Dossier CHRONOS 给药方案 still shows `每2周1次；含负荷剂量` + `第1周至第51周`.

### Non-blocking polish (single list; not this round’s gate)

- `trialLabel()` still has a generic `>12` → `…` fallback for other long names. Current four-trial set does not trigger it.
- Heatmap X labels sit at the **bottom** of the canvas (ECharts default). Awkward reading order, not unreadability.
- 奈莫利珠单抗 给药方案 remains `奈莫利珠单抗；第16周` (thin vs CHRONOS). Fail-closed Chinese, not an axis-label regression. Science call, not this visual task.
- `观察截止：2026-08-30` is the freeze date, not a future placeholder.

Vision over `chromium_nct02260986_1280.png` that the lead is `可下钻到来版本与原文` (missing `源`) is an OCR error. Frozen HTML and live DOM both read **`可下钻到来源版本与原文。`**

### Objections

1. Scoring screenshot OCR of `到来版本` as a new copy blocker would falsely fail a freeze whose HTML is correct.
2. Scoring `data-filter-scope="module"` as user-visible “模块级” would mix implementation attributes with 表体/chrome. User-visible copy has no `模块级`.
3. 740/0 remains the wrong visual proxy; this pass is digest + live DOM + current 00:47 stills.

## Evidence And Assumptions

**Evidence**

- Official digest `bcf4fb22…` on both `site/` and `final-candidate/site/`; 0 diffs; 27 files; `report-c.js` 23221 bytes.
- Live Chromium 1024: grouping/overview axis `奈莫利珠单抗研究` with `ellipsis=[]`; dossier `h1` `NCT02260986 试验档案`; `模块级` HTML count 0; overflowX=0; unsplit `300 mg`/`250 mg`; complete CHRONOS/ADvocate2 periods.
- Current stills dated 2026-08-31 00:47. Historical 1280 overview pair not used.

**Assumptions**

- Canonical tree is this `site/` digest. English INN for Lebrikizumab, NCT, IGA/EASI, CHRONOS/ADvocate2 are 必要缩写.
- 900px remains a fair medical-manager laptop height.
- “图表轴” means the Y-axis trial short name, not the 表体 `试验` column (which may still show the full registry Chinese title).

**Inference**

- Execution closed the remaining axis-ellipsis and dossier-title/filter-copy items without regressing the `4a5c4825` typography closure.
- Remaining items are polish / science, not failed named checks.

**Uncertainty**

- WebKit was inspected via current PNGs, not re-driven live. Residual engine risk is low: Chromium DOM and Chromium/WebKit 1024 grouping stills agree on `奈莫利珠单抗研究` and unsplit `mg`.
- 1920 not re-measured live this round. 1024 overflowX=0 is the named gate.

## Risks, Gaps, And Verification Needs

- 1440 width not live; full filter × URL restore matrix not exhaustively clicked this round.
- Science completeness of CHRONOS 入选 and 奈莫利珠单抗 给药方案 is **out of this visual round**.
- `index.html` still absent.

## Recommended Next Step

Codex **may record visual-conference pass** on digest `bcf4fb22` for this closure. Do **not** reopen earlier blockers. Do **not** revert `report-c.js`. Do **not** promote until Codex records **its** final acceptance. Do **not** expand a new task from this pass.

### Decision points for Codex

1. Canonical tree is `bcf4fb22` on both `site/` and `final-candidate/site/` — **confirmed**.
2. Named repairs: axis `奈莫利珠单抗研究` **通过**; `NCT编号 试验档案` **通过**; 逐试验筛选无“模块级” **通过**; 剂量换行/疗程/1024 无横向拖动 **未回归**.
3. New high/critical blocker from this change: **无**.
4. Visual-conference result: **通过**. Codex keeps final acceptance.

### Bounded questions

None required to close this visual round. Optional: confirm that the 表体 `试验` column may keep the full Chinese trial title while the **chart axis** uses `奈莫利珠单抗研究`.

Safe provisional path if unanswered: keep `bcf4fb22` as the reviewed eighth-repair candidate; this visual conference **passes the named checks**; do not promote until Codex records final acceptance; do not revert C `report-c.js`.

This is the `visual_single_object` conference artifact only. I did not write `runs/conference/.../visual_single_object.md` and did not edit the portal.
