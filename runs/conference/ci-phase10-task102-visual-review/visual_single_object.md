Fallback is `cursor` / `cursor-grok-4.6` as bounded `visual_single_object`. I’ll read the conference contract first, then independently review the three HTML sites without editing artifacts.Authority docs and acceptance artifacts are next: design spec, visual-loop decision, verifier reports, then the actual screenshots.I’ll inspect the required PNGs at 1280 and 1920, then check HTML for Chinese-native leaks and chart-before-table order.# Conference Participant Output: ci-phase10-task102-visual-review - visual_single_object

## Boundary Check

- **Fallback identity:** Codex primary `grok-build / grok-4.6` was unavailable before a resumable session existed. This pass ran as declared `pi` fallback **`cursor` / `cursor-grok-4.6`**. It is not Hermes, not Grok Build, and not final visual authority.
- **Capability limits:** No live Chromium/WebKit click-through, no 1024 px captures (verifier did not produce them), no evidence-drawer interaction, no production writes, no artifact edits. Image-caption OCR is fallible; HTML/JS on disk was used to corroborate. Not every one of 684 PNGs was opened; the required 1280/1920 set plus extras were.
- **Hard boundaries kept:** Read-only under the authorized workspace plus the Task 10.2 acceptance roots. Did not write `runs/conference/.../visual_single_object.md` or sibling files. Did not look at other participant outputs.
- **Role:** Independent medical-manager visual review. Accept/reject only. Codex remains final.

## Independent Work Product

### Decision (advisory, not final)

**否决** Task 10.2 三个站点式 HTML 的医学经理视觉接受。  
浏览器工具 `verify_portal` 的 `ok: true` 只证明路由可加载、机器违规为空，**不能**当作图先表后、首屏可用、矩阵可读或中文原生通过。

通过条件是「无 P0/P1 医学经理可用性缺陷，且默认视野下核心疗效/安全/矩阵图无需横向拖动」。本 pass 已见到多项 P0/P1。安全性热图本身在 1280/1440/1920 未见明显横向拖动，但矩阵页空图使该条无法单独救活整站。

### Highest-impact defect

**A/B/C 核心坐标图在默认首屏是空坐标系**，医学经理打不开「疗效—安全性位置」或「终点×时间点」比较。

| 站点 | 现象 | 证据 |
|---|---|---|
| A `matrix` | 气泡图只有轴线（EASI-75 第16周 × TEAE），图内无气泡；同页表体预置「待计算」 | PNG：`a_matrix__chromium__{1280,1440,1920}`、`a_matrix__webkit__1280`；`matrix.html` 中 `待计算` **190** 次 |
| B `efficacy-safety-matrix` | 同样空气泡图（LDH 应答率第26周 × TEAE） | `b_efficacy-safety-matrix__chromium__{1280,1920}` |
| C `endpoint-timepoint-matrix` | 空热图/坐标（时间点 × 终点） | `c_endpoint-timepoint-matrix__chromium__{1280,1920}` |

对照：C `design-map` 在 1280/1920 能画出散点，说明运行时图表栈不是全面死亡，而是 **矩阵/终点坐标数据未绑定或绑定失败后仍画出空轴**。空轴比「无图」更差：用户以为图坏了或被筛空了。

**建议修复（不改本轮产物，只给 Codex）：**

1. 矩阵/终点图只消费已算好的数值事实；禁止把「待计算」写进受众表。
2. 能配对的点必须画上；不能配对的试验用同页中文原因列表占住图位，**不要**留空白 Cartesian 框。
3. 修复后在 Chromium+WebKit × 1024/1280/1440/1920 重截矩阵页，确认气泡/热图单元格在内容列内完整可见。

### Other P0 / P1 (medical-manager)

**P0 — 内部字段与英文 schema 漏到受众层（违反中文原生与「不得展示后端字段名」）**

- C 筛选与表：「trial_identity」「comparison_logic」「statistical_model」「effect_size」「multiplicity」；表「设计要素」列直接写 `trial_identity`；试验名/内容列为英文 CT.gov 长标题。
- B 筛选：`c3` / `factor-d` / `c5` 与中文靶点并存；`pegasus-cohort`、`extension-through-week-48`、`nct03500549-primary-period`、`baseline_hgb_eligibility_threshold`、`treated` / `period_start` / `analysis`、`other` / `median` / `adherence_summary`；观察指标并列 “Any treatment-emergent adverse event” 与「任何治疗期间不良事件」。
- 披露筛选值虽有中文标签，value 仍是 `reported_value` 一类；若 URL/状态回显原始值，医学经理会看到程序词。

**P0/P1 — 默认首屏层级**

合同：首屏直接看到格局、疗效、安全性、开发状态；标题只留报告/页面名、适应症、观察截止。

- A `overview` 1280/1920（Chromium 与 WebKit）：首屏是竞争格局图 + 靶点计数，**疗效图、安全热图、气泡图都在折页下**；h1 为「创新治疗格局与医学结果」，导语在教用户「先看…再下钻」（解释阅读顺序）。
- B/C 首页 h1 为「首页」，适应症与截止在 meta；首屏被快速筛选/折叠筛选项占用。B 首页图由空 `#kz-chart-module` 运行时注入，1280 上可见格局图，但疗效/安全仍不在同一首屏。
- C 入选标准 1280：首屏几乎全是筛选芯片 + 表，无图。入排页可以表为主，但不得把英文协议名和重复芯片压在结论之前。

**P1 — 图先表后（页面级部分成立，站点级不成立）**

- A 疗效/安全：图在表前，热图格内有数，1280/1920 未见核心图横向拖动。
- A 疗效默认仅约 3 根柱（度普利尤单抗 / 利特昔替尼 / 乌帕替尼），与「默认显示全部 38 项」筛选文案冲突，空白过大。
- A 矩阵：图在表前，但图空、表为占位。
- B 处置总览：流转图在前，可用。
- B 基线人口学 1280：表先行、大量「未公开」，未见基线图。
- C overview DOM：`#kz-c-chart-visuals` 在完整表前，符合结构；矩阵页图空。

**P1 — 跨 A/B/C 不一致**

- A：扁平导航 +「更多」；B/C：分组下拉。页头、筛选、证据抽屉（A `kz-evidence-panel` vs B/C `kz-evidence-drawer`）不是同一套交互语法。
- 日期：「观察截止：2026-07-31」ISO；页脚「数据截至 2026年07月31日」。截图里出现过 `2026-09-01`，与页脚 7 月 31 日并读会让医学经理怀疑截止点。
- 产品芯片：中文通用名、INN、代码名混用；C 来布利珠单抗芯片重复。
- B `pegcetacoplan（C3抑制剂）` 无中文通用名；A 大量仅 INN（Amlitelimab 等）可保留 INN，但应有中文角色/靶点衬字。

**P2（不单独否决，但叠在 P0 上）**

- 矩阵/设计图谱画布过高、留白过大。
- 试验详情 h1「试验档案」而非正式研究名+登记号。
- 未抽查全部产品/试验路由和抽屉打开态。

### Recommended accept/reject by site

| 站点 | 建议 | 一句话 |
|---|---|---|
| A | **否决** | 矩阵空图 + 190×「待计算」；首页首屏看不到疗效/安全 |
| B | **否决** | 疗效—安全性矩阵空图；筛选层英文/字段名；基线表先于图 |
| C | **否决** | 终点×时间点空图；`trial_identity` 等进入表和筛选；英文方案标题 |

安全性热图（A/B 抽查）在已有宽度下**不像**需要横向拖动的失败项；不要用「热图还行」覆盖矩阵失败。

## Evidence And Assumptions

### Evidence (inspected)

**Authority:** `contracts/kangzhe/design_specs/project_profile.md` §§1–3, 10；`docs/decisions/0012-pre-delivery-visual-finalization-loop.md`。

**Verifier (deterministic, not visual accept):**

- A: `ok: true`, 50 routes, chromium+webkit, 1280×800 / 1440×900 / 1920×1080, 300 PNG。
- B: `ok: true`, 32 routes, 192 PNG。
- C: `ok: true`, 32 routes, 192 PNG。
- 无 1024 视口（合同 §10 要求 1024/1280/1440）。

**PNGs actually opened (path under `.../verification/{A,B,C}/v1/screenshots/`):**

- A 1280: overview, efficacy, safety, matrix, landscape, products_dupilumab; overview webkit 1280; matrix webkit 1280。
- A 1920: overview, efficacy, safety, matrix。
- A 1440: matrix。
- B 1280: overview, efficacy, safety, efficacy-safety-matrix, baseline-overview, baseline-demographics, disposition-overview。
- B 1920: overview, efficacy-safety-matrix。
- C 1280: overview, design-map, endpoint-timepoint-matrix, trials_nct03569293, inclusion-criteria。
- C 1920: overview, design-map, endpoint-timepoint-matrix, trials_nct03569293。

**HTML/JS corroboration:**  
`a-real/reports/A/v1/html/{overview,efficacy,matrix}.html` + `assets/report-a.js`；`b-real/.../{overview,efficacy-safety-matrix}.html`；`c-real/.../{overview,endpoint-timepoint-matrix}.html`。

### Assumptions / inference (not evidence)

- 空图主因更像**数值未写入坐标编码**（A 表「待计算」），不是单浏览器 canvas 失败（webkit 同样空；C 设计图谱有点）。
- 图像描述曾把 C 说成「斑块状银屑病」；**磁盘 HTML 与入选标准截图均为中重度特应性皮炎**。以磁盘与后开截图为准，前次 OCR 作废。
- 未打开的路由默认「可能还有同类筛选/中文问题」，不记为已证实缺陷。
- 本角色不裁定科学对错或监管结论。

## Risks, Gaps, And Verification Needs

1. **机器通过 vs 视觉否决：** 若 Codex 用 `report.json ok` 放行，会把空矩阵和「待计算」交给医学经理。
2. **1024 未测：** 热图/气泡在 1024 是否溢出未知；合同明确要求。
3. **未做：** 筛选联动、URL 状态、证据抽屉、200% 缩放、键盘焦点、`prefers-reduced-motion`、全产品/试验页。
4. **截止日文案** 7-31 vs 截图 9-01：需核对 snapshot 观察截止是否与页头一致。
5. **C 适应症：** 本包是 AD 设计比较。若 Task 10.2 真实来源应为银屑病，则还要加一条来源错配（本 pass 未证实该意图）。

## Recommended Next Step

Codex 应 **否决本轮视觉放行**，阻断正式交付目录迁移。最短恢复（生成侧，非本角色改文件）：

1. 重算并绑定 A/B 气泡与 C 终点—时间点矩阵；删除受众「待计算」；无点则改无数据版式。
2. 中文词典覆盖全部筛选/表头/设计要素；禁止 schema id 原文。
3. 压缩 A/B/C 首页 800px 首屏：格局 + 疗效图 + 安全热图（C 为设计图谱）同时可见；筛选默认收起。
4. 补 1024，并重跑矩阵/首页 Chromium+WebKit 截图后，再开一轮隔离视觉审阅。

### Objections to the apparent plan

- 主场计划文件仍是 TODO 骨架，不能当作已审过的视觉结论。
- 「全站验收通过」文案与空矩阵并存，反对把 verifier 当视觉闸门。
- 反对用拆字号或裁切来塞矩阵；应绑定数据或改无数据版式。
- 反对三站分别「热图过了就算过」；通过条件是整站无 P0/P1。

### Decision points for Codex

1. 本轮三站视觉结论是否采纳本角色的 **否决**？
2. 空矩阵算渲染缺陷还是允许的数据缺口？即便是缺口，空轴图仍应否决。
3. 是否要求补 1024 才允许复审？

### Bounded questions

1. C 的锁定适应症是否就是中重度特应性皮炎？若应为银屑病，请给出 snapshot id。
2. A 矩阵「待计算」是生成器未写事实，还是有意等运行时计算而运行时没跑？
3. 页头「观察截止：2026-09-01」与页脚「2026年07月31日」哪一个是锁定观察截止？

**Safe provisional path:** 视为三站均未通过视觉接受；不修改产物；等待 Codex 复审/派修复。本 conference pass 完成。
