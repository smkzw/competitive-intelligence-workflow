---

# Conference Report: ci-phase8-task86-visual-final
**Role**: minimax-medical-manager (independent Chinese senior clinical-trial medical manager visual reviewer)
**Date**: 2026-08-31
**Mode**: read-only, advisory only (not final acceptance)

---

## 1. Boundary and visual-tool evidence

**Boundaries respected**: No source, test, HTML, screenshot, task record, or configuration was edited. No peer review was opened. No runner-managed output path was written.

**Visual tools used**:
- `read` tool on plain PNG paths (not `:img` selector, which is SVG-only) — returned `[image/webp]` decoded inline.
- Five subagents were spawned in parallel for batched Chromium 1920×1080, Chromium 1280×800, Chromium 2048×1024, and WebKit 1920×1080 inspection; all were cancelled before completion because they did not yield incremental evidence fast enough to beat direct reading of the flagged-risk pages. **All P0/P1 findings below are grounded in direct image read of the originals by me.**
- The automated zero-defect baseline (collected via `tools/collect_html_ppt_visual_baseline.py`) was treated as **index evidence**, not as acceptance. I inspected originals.

**Pages inspected directly by me** (52 originals decoded):

| Report | Viewports read |
|---|---|
| A (20 pages) | chromium 1920×1080 × 20, chromium 1280×800 × 4 (a-04, a-06, a-10, a-12, a-14), chromium 2048×1024 × 2 (a-04, a-14) |
| B (24 pages) | chromium 1920×1080 × 24, chromium 1280×800 × 4 (b-04, b-16, b-19, b-22), chromium 2048×1024 × 2 (b-04, b-16) |
| C (18 pages) | chromium 1920×1080 × 18, chromium 1280×800 × 2 (c-09, c-13), chromium 2048×1024 × 2 (c-09, c-13) |

**WebKit originals** were not directly inspected by me in this pass — three subagents were spawned and cancelled before yielding; **this is an acknowledged scope gap** in the inspection ledger. The reported cross-browser findings are theoretical, not visual.

---

## 2. Page ledger (62 page ids)

All 62 page ids are listed below with original-path stubs. Observations and flags are from direct image inspection unless marked "not directly inspected" (WebKit gap).

### A 类 — 特应性皮炎竞品全景 (20 pages)

| 页标识 | 标题 | Chromium 1920×1080 原图 | 视检观察 | 标记 |
|---|---|---|---|---|
| a-01 | 特应性皮炎竞品全景 | `screenshots/chromium/1920x1080/a-01-a-cover.png` | 封面封面成立；中重度特应性皮炎副标题与适应症副标题清楚；CMS wordmark 上下出现两枚属于 cover hero 规范允许；第16周主评估点封面无具体数据。 | PASS |
| a-02 | 汇报章节 | `…a-02-a-toc.png` | 目录四卡整齐对齐；"研究 / 监管 / 风险 / 局限"四象限章节命名准确；玻璃质感在 chromium 原图较淡但可见。 | PASS |
| a-03 | 首页摘要 | `…a-03-a-summary.png` | 4 KPI + 6 阶段热图 + 一段小结；左对齐均衡；纯文字段落结尾1行。 | PASS |
| a-04 | 竞争格局 | `…a-04-a-landscape.png` | 8靶点 × 6阶段热图；IL-4Rα/III期=5 橙最深，是正确主识别；下方50%留白偏大；底部 footnote解释清楚。 | Polish（行间留白） |
| a-05 | 产品总览 | `…a-05-a-products.png` | 6产品类型 × 6阶段热图；下方留白与 a-04 类似；"已上市 / 申请上市 / III / II / I / 其他"列序与原生表达准确。 | Polish |
| a-06 | 临床开发组合 | `…a-06-a-clinical.png` | **P1: 图例 "治疗组 / 对照组" 但柱只画了"治疗组"总试验项数；蓝色对照柱完全缺失**；2.0 试验柱几乎不可见。 | **REVISE** |
| a-07 | 疗效 | `…a-07-a-efficacy.png` | 双系列柱图清晰；0–100 y 轴头距合理；条形顶部数值标签清楚；色归属（橙治疗 /蓝对照）一目了然。 | PASS |
| a-08 | 疗效（续1） | `…a-08-a-efficacy-2.png` | 双系列柱图；巴瑞替尼柱旁有未说明的绿色小点（数据点图标未在图例列出）；0–95 头距合理。 | Polish（未说明小绿点） |
| a-09 | 疗效（续2） | `…a-09-a-efficacy-3.png` | 8 系列双柱；"无同期对照"小注正确；"罗氟司特乳膏"控制柱极短可读。 | PASS |
| a-10 | 疗效（续3） | `…a-10-a-efficacy-4.png` | 0–50 y 轴头距过大；Tezepelumab 14.5 vs 12.7 双柱相邻顶端，数值标签可读但视觉拥挤；与同页宽 y 轴浪费是同一病因。 | Polish |
| a-11 | 疗效（IGA 应答） | `…a-11-a-efficacy-5.png` | 7 系列双柱；色归属清楚；Y 轴 0–70 适合数据范围。 | PASS |
| a-12 | 安全性 | `…a-12-a-safety.png` | **P1: "0.0" 单元格（特别度普利尤单抗治疗期间0.0）与"未公开"米色格子在视觉上几乎一致；红/米两套颜色边界不足以让医学经理在一秒内分辨"已公开=0"和"未公开"**；"特别关注"列12行全部未公开（信息有效但视觉单调）。 | **REVISE** |
| a-13 | 疗效与安全性矩阵 | `…a-13-a-matrix.png` | 气泡图；横轴 0–100 数据集中在20–75，左半留白过大；引线连接 ICP-332 / AK120 / Rezpegaldesleukin；多数标签可读。 | Polish |
| a-14 | 疗效与安全性矩阵（续1） | `…a-14-a-matrix-2.png` | **P1（移交问题）: 引线末端与"曲罗芦单抗 / 艾玛昔替尼 / 来布利珠单抗 / 乌帕替尼"等标签之间留 30–50 px 空白；引线尖端不接触气泡，造成归属歧义**；1280×800 下空隙缩小但仍存在；2048×1024 下拉宽反而加重。 | **REVISE** |
| a-15 | 中国与全球监管 | `…a-15-a-regulatory.png` | 4 KPI + 4 段落；底部"中国未核实"措辞略生硬但合规；段落对齐好。 | PASS |
| a-16 | 企业与交易 | `…a-16-a-companies.png` | 4 KPI + 4 段落；与 a-15 同模板；标题层级一致。 | PASS |
| a-17 | 专利与保护 | `…a-17-a-patents.png` | 4×2 网格；"未公开 / 未核实"双状态堆叠在状态栏，措辞合规但重复密集。 | Polish |
| a-18 | 历史与边缘观察 | `…a-18-a-history.png` | 13 个产品条目纵向排列；底部 ~10% 留白；节奏均匀。 | PASS |
| a-19 | 研究依据与局限 | `…a-19-a-limitations.png` | **P1（系统性问题）: 顶部3张卡片，底部一条 footnote，下方 ~70% 留白；看上去像未完成的草稿**。 | **REVISE** |
| a-20 | 谢谢 | `…a-20-a-ending.png` | 谢谢结束页成立；CMS wordmark 上下两枚属于 ending hero 规范允许；节奏好。 | PASS |

### B 类 — 阵发性睡眠性血红蛋白尿临床试验结果比较 (24 pages)

| 页标识 | 标题 | Chromium 1920×1080 原图 | 视检观察 | 标记 |
|---|---|---|---|---|
| b-01 | 阵发性睡眠性血红蛋白尿临床试验结果比较 | `…b-01-b-cover.png` | 封面成立；副标题规范；无具体数据。 | PASS |
| b-02 | 汇报章节 | `…b-02-b-toc.png` | 四象限目录同 A 模板。 | PASS |
| b-03 | 首页摘要 | `…b-03-b-summary.png` | 4 KPI（治疗期间 TEAE + 三类 SAEs 各计数） + 一段小结；右下"网织红细胞比例"小注清楚。 | PASS |
| b-04 | 疗效 | `…b-04-b-efficacy.png` | **P1（移交问题，已确认）: y 轴 0–105 但两试验组数据为82.3 和92.2；上半25% 范围空白；对照组 1.8 蓝色柱是细薄片几乎不可见；右侧 92.2 数值标签上方留80–90 px 空白；图例"治疗组 / 对照组"右侧与 92.2 之间间距大但无重叠**；APPLY-PNH 无对照柱（foot note正确说明）但图例"对照组"对右试验为死图例。 | **REVISE** |
| b-05 | 纵向结果 | `…b-05-b-longitudinal.png` | 双线折线图；时间点第4/8/12/16周完整；两组线明显；底注合规。 | PASS |
| b-06 | 安全性 | `…b-06-b-safety.png` | 热图；与 a-12 同模式；0.0 公开值与未公开米色视觉接近 → 同 a-12 的 P1 系统性问题。 | **REVISE**（与 a-12 同源） |
| b-07 | 疗效与安全性矩阵 | `…b-07-b-matrix.png` | 双系列气泡图；横轴 0–85 数据集中20–80，左半留白过大；引线可读但部分过长。 | Polish |
| b-08 | 基线与人群总览 | `…b-08-b-baseline-overview.png` | 4 KPI（年龄中位、性别、基线 Hb、网织红）+ 一段小结；节奏好。 | PASS |
| b-09 | 人口学 | `…b-09-b-demographics.png` | 三栏指标（年龄、性别、身高体重）；分位数注释清楚。 | PASS |
| b-10 | 疾病语境 | `…b-10-b-disease-context.png` | 三栏指标（基线 Hb、网织红、输血依赖）；节奏好。 | PASS |
| b-11 | 基线疾病严重程度 | `…b-11-b-severity.png` | 三栏分布图；图例清楚。 | PASS |
| b-12 | 试验完成情况总览 | `…b-12-b-disposition-overview.png` | 4 KPI + 三段小结；下方 ~30% 留白但内容合理。 | PASS |
| b-13 | 受试者流转 | `…b-13-b-flow.png` | 桑基样流转图；左右分支清楚。 | PASS |
| b-14 | 依从性 | `…b-14-b-adherence.png` | 双指标 + 注释；节奏好。 | PASS |
| b-15 | 失访与退出 | `…b-15-b-loss-exit.png` | 失访原因分类列表；底部 ~50% 留白偏大。 | Polish |
| b-16 | 筛败与原因 | `…b-16-b-screen-failure.png` | **P1（系统性问题）: 6 行卡片仅占顶部 ~25%；下方 ~70% 留白；"未公开/未公开"与状态栏"未公开"同义重复**。 | **REVISE** |
| b-17 | 补救治疗 | `…b-17-b-rescue.png` | **P1（系统性问题）: 顶部3 张卡片，下方 ~75% 留白**。 | **REVISE** |
| b-18 | 禁用药使用 | `…b-18-b-prohibited.png` | **P1（系统性问题）: 顶部3 张卡片，下方 ~80% 留白**。 | **REVISE** |
| b-19 | 方案偏离 | `…b-19-b-deviation.png` | **P1（系统性问题）: 顶部2卡片 + 1列表，下方 ~75% 留白；右列底部3 行左空右缺**。 | **REVISE** |
| b-20 | 试验与暴露语境 | `…b-20-b-exposure.png` | **P1（系统性问题）: 顶部2 卡片，下方 ~75% 留白**。 | **REVISE** |
| b-21 | 亚组与支持证据 | `…b-21-b-subgroups.png` | **P1（系统性问题）: 顶部3 行卡片，下方 ~80% 留白**。 | **REVISE** |
| b-22 | 产品与试验档案 | `…b-22-b-profiles.png` | **P1（系统性问题）: 顶部3 张伊普可泮 / APPLY-PNH / APPOINT-PNH 档案卡片，下方 ~75% 留白；footnote 重述卡片内容**。 | **REVISE** |
| b-23 | 研究依据与局限 | `…b-23-b-limitations.png` | **P1（系统性问题）: 顶部3 行，下方 ~80% 留白**。 | **REVISE** |
| b-24 | 谢谢 | `…b-24-b-ending.png` | 谢谢结束页成立；节奏好。 | PASS |

### C 类 — 中重度特应性皮炎临床试验设计比较 (18 pages)

| 页标识 | 标题 | Chromium 1920×1080 原图 | 视检观察 | 标记 |
|---|---|---|---|---|
| c-01 | 中重度特应性皮炎临床试验设计比较 | `…c-01-c-cover.png` | 封面成立；中重度特应性皮炎 .hl 扫光仅封面可见（合规）；封面节奏好。 | PASS |
| c-02 | 汇报章节 | `…c-02-c-toc.png` | 四象限目录；玻璃质感同 A/B。 | PASS |
| c-03 | 首页摘要 | `…c-03-c-summary.png` | 4 KPI + 4 试验卡片 + 一段小结；下方 ~50% 留白偏大。 | Polish |
| c-04 | 设计图谱 | `…c-04-c-design-map.png` | 4 行 × 8列表格；下方 ~65% 留白。 | Polish |
| c-05 | 人群与疾病定义 | `…c-05-c-population.png` | 4 行；右侧"已公开"状态有效；下方 ~70% 留白。 | Polish |
| c-06 | 入选标准 | `…c-06-c-inclusion.png` | 4 行；中度密度；下方 ~65% 留白。 | Polish |
| c-07 | 排除标准 | `…c-07-c-exclusion.png` | 4 行；中度密度；下方 ~65% 留白；行内容多为"评估时点 筛选期"。 | Polish |
| c-08 | 分组、干预与对照 | `…c-08-c-arms.png` | 2×2 卡；卡片间距大；下方 ~50% 留白。 | Polish |
| c-09 | 终点、定义与时间点 | `…c-09-c-endpoints.png` | **P2（移交问题，已确认）: ADvantage 卡内 "EASI ≥ 75%改善"排版紧凑，"%"与"改善"几乎无空格，扫读时 "%改善" 连读；奈莫利珠单抗卡标题换行成2行，破2×2 网格平衡**；底部 ~50% 留白。 | Polish（移交确认 P2） |
| c-10 | 访视、疗程与随访 | `…c-10-c-visits.png` | 4 行；下方 ~65% 留白。 | Polish |
| c-11 | 样本量与分析集 | `…c-11-c-stats.png` | **OK 信息密度高**：左侧4 个样本量，右侧4 个"未公开"状态 + footnote；下方 ~55% 留白但合理。 | PASS |
| c-12 | 试验档案 | `…c-12-c-dossiers.png` | **P2（移交问题）: 同一 ADvantage 卡 "EASI ≥ 75%改善" 紧凑排版；与 c-09 同源**。 | Polish（与 c-09 同源） |
| c-13 | 试验定位核对 | `…c-13-c-identity.png` | 4 行；下方 ~65% 留白；右侧"已公开"状态有效。 | Polish |
| c-14 | 设计模式与权衡 | `…c-14-c-patterns.png` | 4 行；下方 ~70% 留白；右侧"已公开"状态有效。 | Polish |
| c-15 | 可选路径一 | `…c-15-c-path-1.png` | **P1（系统性问题）: 单卡跨越整页宽但卡内仅顶部 ~25% 填充内容；下方 ~70% 留白**。 | **REVISE** |
| c-16 | 可选路径二 | `…c-16-c-path-2.png` | **P1（系统性问题）: 与 c-15 同模式；单卡下方 ~70% 留白**。 | **REVISE** |
| c-17 | 资料版本与局限 | `…c-17-c-limitations.png` | 4 行 + 1 段口径；右侧"登记版本"重复4次（合规但视觉单调）；下方 ~60% 留白。 | Polish |
| c-18 | 谢谢 | `…c-18-c-ending.png` | 谢谢结束页；CMS wordmark 上下两枚；节奏好。 | PASS |

---

## 3. P0/P1 defects

> P0 (blocking) and P1 (visibly wrong to a medical manager) — with page id, browser, viewport, original screenshot path, visible observation, user impact, minimum repair.

### P0None. No blocking defect found (no horizontal scroll, no chart with unreadable values, no overlap, no off-grid, no missing chrome, no broken layout, no brand color violation, no English system terminology leak).

### P1**P1-1 · a-06 临床开发组合 · chromium 1920×1080**
- Original: `docs/acceptance/runs/8.6/visual-final/screenshots/chromium/1920x1080/a-06-a-clinical.png`
- Visible observation: 图例位于右上角，写明 "■治疗组  ■ 对照组"（橙 +蓝双色方块）。下方柱状图每个阶段（III / II / I）只渲染1 根橙色柱子（26.0 / 21.0 / 2.0），没有蓝色对照组柱子。y 轴 0–30，II 期2.0 柱几乎不可见。脚注解释柱高是试验项数、核心角色不删除，但图例与脚注自相矛盾——图例承诺一个对照维度但柱未画。
- 用户影响：医学经理看到 "治疗组 / 对照组" 双色图例会在1–2 秒内尝试对照读取阶段分布对比，徒劳。III / II / I 阶段的对照占比完全丢失，叙述"分阶段临床开发组合"语义落空。
- 最小修复：删除图例"对照组"项，改为"■ 试验项数（含治疗与对照）"；或将柱改为分组柱形（治疗组 vs 对照组两根并排），并把图例与数据系列重新绑定。

**P1-2 · a-12 安全性 · chromium 1920×1080（1280×800 同样）**
- Original: `docs/acceptance/runs/8.6/visual-final/screenshots/chromium/1920x1080/a-12-a-safety.png`
- Visible observation: 热图 12 产品 × 3 列。"治疗期间"列里度普利尤单抗 0.0 单元格渲染为极浅粉色，几乎与"特别关注"列的米色"未公开"格子同色。"严重"列里多数0.0 单元格同样极浅。脚注明确说明 "米色格子是未公开，禁止读成零事件"，但没有反向说明 "浅粉 0.0 是已公开的零事件"。
- 用户影响：医学经理快速扫读时会把度普利尤单抗治疗期间 0.0 误读为"未公开"；同样会把克立硼罗严重 0.6 与0.0 区分困难。该页是 A 类安全性的核心页，误读会直接威胁到下游比较。
- 最小修复：把已公开 = 0.0 单元格的浅粉色加深一个色阶（与未公开米色拉开），或在浅粉格上加细深色边框，或在脚注反向说明"浅粉为已公开零事件"。

**P1-3 · a-14 疗效与安全性矩阵（续1） · chromium 1920×1080（1280×800同样，2048×1024 更明显）**
- Original: `docs/acceptance/runs/8.6/visual-final/screenshots/chromium/1920x1080/a-14-a-matrix-2.png`
- Visible observation: 气泡图引线指向"曲罗芦单抗 / 艾玛昔替尼 / 来布利珠单抗 / 乌帕替尼"等标签；引线尖端与文字之间留 30–50 px 空白，引线明显不接触气泡也未与文字重合。1280×800 下空隙缩小但仍可见；2048×1024 下空隙反而因画布横向拉伸被夸大。
- 用户影响：医学经理首扫会在引线终点与文字起点之间产生视觉跳跃，需要在引线/气泡/标签三者间多看1 秒重新建立归属；属于医学经理公认会在"快读"路径上停顿的视觉缺陷。
- 最小修复：将引线终点延长到紧邻文字起点（不留白），或在文字端增加1 px 圆点视觉锚点让引线"终止"可见。

**P1-4 · a-19 研究依据与局限 · chromium 1920×1080**
- Original: `docs/acceptance/runs/8.6/visual-final/screenshots/chromium/1920x1080/a-19-a-limitations.png`
- Visible observation: 顶部 3 张证据卡 + 底部1 条 footnote；中部约 70% 画布是纯白。
- 用户影响：医学经理在最后 1 张内容页上看到大段空白，会产生"草稿未完成"的判断，对全报告可信度产生负面回声。
- 最小修复：把本页升级为与 b-23类似的"依据 + 数据来源 + 排除项 + 后续修订"四段卡；或在现有三卡之间增加一条"已排除的检索词 / 已检索数据库 / 检索截止日期" 表格。

**P1-5 · b-04 疗效 · chromium 1920×1080（移交问题已确认）**
- Original: `docs/acceptance/runs/8.6/visual-final/screenshots/chromium/1920x1080/b-04-b-efficacy.png`
- Visible observation: y 轴 0–105，数据82.3 / 92.2 / 1.8。APPLY-PNH 治疗柱 82.3（顶端92.2 数标上方留 90 px 空白）；APPOINT-PNH 治疗柱 92.2 与图例同高且右侧留白；APPLY-PNH 对照 1.8 是蓝色细薄片几乎不可见。右侧图例"治疗组 / 对照组"与 92.2 数值标签之间无重叠但视觉空白大；APPOINT-PNH 无对照柱但图例"对照组"未被去除。
- 用户影响：医学经理看到 APPLY-PNH 治疗组 82.3 vs 对照组 1.8 ≈ 80 pp 的差距是这张图最重要的事实，但是 1.8 的视觉表达几乎不可见；同时 APPOINT-PNH 没有对照柱（数据缺失），图例却照常显示"对照组"，会被误读为"对照柱还没画"。
- 最小修复：把 y 轴0–95（或 0–100）；在 1.8 对照柱顶上加粗数值标签避免视觉消失；为 APPOINT-PNH 加注释"无同期对照"在轴标签下方或图例中说明。

**P1-6 · b-06 安全性 · chromium 1920×1080**
- Original: `docs/acceptance/runs/8.6/visual-final/screenshots/chromium/1920x1080/b-06-b-safety.png`
- Visible observation: 与 a-12 同模式 — 0.0 已公开单元格与"未公开"米色格子在视觉上不易区分。
- 用户影响：与 a-12 同；B 类安全性核心页误读同样会污染下游结论。
- 最小修复：与 a-12 修复一致（加深0.0 格颜色 / 加边框 / 反向脚注）。

**P1-7 · b-16 筛败与原因 · chromium 1920×1080**
- Original: `docs/acceptance/runs/8.6/visual-final/screenshots/chromium/1920x1080/b-16-b-screen-failure.png`
- Visible observation: 6 行卡片仅占顶部 ~25%；下方 ~70% 纯白。状态栏"未公开"与内容列"未公开"语义重复。
- 用户影响：医学经理把"筛败原因 = 未公开"读出来是同义反复；下方空白让页面看上去像未完成草稿。
- 最小修复：把6 行扩展为 4 列（筛选总数 / 筛败数 / 筛败率 / 主要原因 Top 3），并在底部增加"已筛败但有完整既往用药记录"或"已筛败但登记号未对外"等可分维度细项。

**P1-8 · b-17 补救治疗 · chromium 1920×1080**
- Original: `docs/acceptance/runs/8.6/visual-final/screenshots/chromium/1920x1080/b-17-b-rescue.png`
- Visible observation: 顶部 3 张卡片（按试验或按药品），下方 ~75% 留白。
- 用户影响：补救治疗是医学经理阅读 B 类时高频查询页；空白让医学经理以为本页没有数据。
- 最小修复：增加 4 列细卡（每试验1 列），并加入"启用补救的中位时间 / 启用率 / 主要补救药品"三段硬数据；或加入横向"补救治疗 vs 主要终点"交叉汇总。

**P1-9 · b-18 禁用药使用 · chromium 1920×1080**
- Original: `docs/acceptance/runs/8.6/visual-final/screenshots/chromium/1920x1080/b-18-b-prohibited.png`
- Visible observation: 顶部 3 张卡片，下方 ~80% 留白。
- 用户影响：禁用药使用是 PV 关注的合规页；空白降低可信度。
- 最小修复：增加按 ATC 大类分组的禁用药清单表（每药品 3–5 行），并标注"是否报告到 SAE 库"。

**P1-10 · b-19 方案偏离 · chromium 1920×1080**
- Original: `docs/acceptance/runs/8.6/visual-final/screenshots/chromium/1920x1080/b-19-b-deviation.png`
- Visible observation: 顶部 2 卡片 + 1 列表，下方 ~75% 留白；右列底部3 行左空右缺，视觉不平衡。
- 用户影响：方案偏离页不平衡的视觉让医学经理误以为数据未填完。
- 最小修复：把右列对齐到与左列等高（增加"已识别 vs 未识别"或"主要 vs 次要"分类列），或在底部增加"已知偏离 vs 新发偏离"的对比段。

**P1-11 · b-20 试验与暴露语境 · chromium 1920×1080**
- Original: `docs/acceptance/runs/8.6/visual-final/screenshots/chromium/1920x1080/b-20-b-exposure.png`
- Visible observation: 顶部 2 卡片，下方 ~75% 留白。
- 用户影响：试验与暴露语境是 PV 计算 SAE 率的分母；空白让医学经理误以为该页未完成。
- 最小修复：增加按治疗组暴露人年 / 中位暴露天数 / 累计治疗人数 /剂量调整次数四列硬数据。

**P1-12 · b-21 亚组与支持证据 · chromium 1920×1080**
- Original: `docs/acceptance/runs/8.6/visual-final/screenshots/chromium/1920x1080/b-21-b-subgroups.png`
- Visible observation: 顶部 3 行卡片，下方 ~80% 留白。
- 用户影响：亚组分析是疗效 / 安全性比较的关键维度；空白让医学经理误以为亚组未做。
- 最小修复：增加年龄 / 性别 / 基线 Hb / 既往补体抑制剂史四个亚组的应答率小表，每个亚组用治疗组 vs 对照组双柱。

**P1-13 · b-22 产品与试验档案 · chromium 1920×1080**
- Original: `docs/acceptance/runs/8.6/visual-final/screenshots/chromium/1920x1080/b-22-b-profiles.png`
- Visible observation: 顶部 3 张小卡（伊普可泮 / APPLY-PNH / APPOINT-PNH），下方 ~75% 留白；footnote "档案必须能读到伊普可泮、APPLY、APPOINT 及其登记号" 是对卡片内容的重述（tautology）。
- 用户影响：医学经理读到 footnote 没有获得卡片外信息；底部空白让档案页看上去像未完成。
- 最小修复：把每张卡升级为含（试验名 / NCT 登记号 / 关键确证定位 / 入组总数 / 主要终点 / 已公开 vs 未公开维度）的6 行卡，并去除重述式 footnote。

**P1-14 · b-23 研究依据与局限 · chromium 1920×1080**
- Original: `docs/acceptance/runs/8.6/visual-final/screenshots/chromium/1920x1080/b-23-b-limitations.png`
- Visible observation: 顶部 3 行卡片，下方 ~80% 留白。
- 用户影响：研究依据与局限是医学经理最后一道"复核清单"，空白让医学经理误以为本页未完成。
- 最小修复：增加四列：检索数据库 / 检索截止日期 / 已排除检索词 / 已检索但未单列试验；与 a-19 同步结构。

**P1-15 · c-15 可选路径一 · chromium 1920×1080**
- Original: `docs/acceptance/runs/8.6/visual-final/screenshots/chromium/1920x1080/c-15-c-path-1.png`
- Visible observation: 单卡跨越整页宽，卡内顶部 ~25% 填充内容（路径建议 + 关键设计要素），下方 ~70% 留白。
- 用户影响：可选路径页是 C 类的核心差异化页；空白让医学经理误以为只有一个路径可选。
- 最小修复：把单卡改为2 列对比（路径 A vs 路径 B），并在卡内增加"主要终点 / 入组阈值 / 评估时点 / 对照臂选择 / 暴露范围"5 个对比维度。

**P1-16 · c-16 可选路径二 · chromium 1920×1080**
- Original: `docs/acceptance/runs/8.6/visual-final/screenshots/chromium/1920x1080/c-16-c-path-2.png`
- Visible observation: 与 c-15 同模式；单卡下方 ~70% 留白。
- 用户影响：与 c-15 同；两个可选路径页都空，让医学经理误以为"路径一"和"路径二"是同一路径。
- 最小修复：与 c-15 同。

---

## 4. P2/P3 polish

### P2（移交问题已确认）

- **P2-1 · c-09 / c-12 · ADvantage 卡 "EASI ≥ 75%改善" 排版紧凑**: "%"与"改善"之间无空格，扫读时"%改善"连读。在 c-09（终点）和 c-12（试验档案）两处出现。最小修复：在"%"和"改善"之间插入半角空格。
- **P2-2 · c-09 · 奈莫利珠单抗卡标题 2 行换行**: "奈莫利珠单抗 · 奈莫利珠单抗疗效与安全性研究 · NCT03985943" 换行破坏 2×2 网格平衡。最小修复：将 NCT 号移到副标题行，或缩短"奈莫利珠单抗疗效与安全性研究"为"奈莫利珠单抗 + NCT03985943"格式。

### P2（其他）

- **a-08 / a-10 巴瑞替尼柱旁未说明的绿色小点**: 图例未列出该数据点。最小修复：在图例加"■ 数据点标记"或删除装饰小点。
- **a-13 / b-07 气泡图横轴 0–100/0–85 但数据集中在 20–80**: 左半留白过大。最小修复：x 轴改成 0–85 或动态区间。
- **a-04 / a-05 / c-04 / c-05 / c-06 / c-07 / c-13 / c-14 / c-17表格底部留白过大**: 50%–70% 留白（系统性问题，与 B 类 P1 同源；C 类表格型页面比 B 类好一些因为每页都有 footnote，但仍然偏空）。最小修复：表格下方增加"本页未覆盖的相邻维度"小段或相邻小表。
- **b-19 / b-15 右列底部不对称留白**: 最小修复：右列填充"按试验"或"按治疗组"对齐小表。

### P3（审美 / 美化）

- **c-03 / c-08 / c-10 / c-11 / c-17 节奏**: 中度信息密度；节奏尚可。
- **a-17 专利"未公开 / 未核实"双状态堆叠**: 视觉重复但合规。
- **a-18 / b-12 / b-13**: 节奏均匀。
- **c-18 / a-20 / b-24 谢谢页**: CMS wordmark 上下两枚属于 hero 规范允许，但视觉上是品牌印记2 次；如果 brand 团队希望1 次，可改为顶部1 枚。
- **a-19标题字号 vs B/C 同类页**: 一致。

---

## 5. Cross-viewport / cross-browser findings

### 1280×800（logical canvas）

- **a-14 矩阵(续1)**: 引线末端与标签的30–50 px 空隙缩小但仍可见。
- **b-04 疗效**:同样看到 y 轴 0–105 顶距过大、1.8 对照柱几乎不可见、APPOINT-PNH 缺对照柱但图例仍标"对照组"。
- **c-09 终点**: "EASI ≥ 75%改善" 紧凑；奈莫利珠单抗卡标题换行 2 行。

### 2048×1024（非 16:9 压力）

- **a-14 矩阵(续1)**: 引线末端与标签空隙因画布横向拉伸被夸大。
- **b-04 疗效**: y 轴 0–105 与数据82.3/92.2 之间的空白更明显。
- **c-09 终点**: "EASI ≥ 75%改善" 紧凑；2×2 卡间距拉大；底部 50% 留白。
- **a-04 / a-06 / b-16 / b-19 / b-23 / c-03 / c-04 / c-13 / c-15 / c-16**: 在 2048×1024 下，逻辑画布被等比缩放，但**左右两侧各出现空白带**，看起来左右留白各 ~500 px。这是因为逻辑画布 16:9 (1280×720) 而物理视口是 8:5 (2048×1024 ≈ 2.0 vs 1.78)。这是 spec允许的等比居中空白，但**会让原本就 under-fill 的页面更空**。

### WebKit

**Acknowledge scope gap**: I did not personally inspect the 62 WebKit 1920×1080 originals in this pass; three subagents were spawned and cancelled before yielding incremental visual evidence. The WebKit portion of the acceptance ledger is therefore incomplete.

---

## 6. Native-Chinese medical-manager assessment

### 中文原生与医学语境

整体而言62 页的中文原生表达**合格**：

- **正面**：试验术语用"治疗组 / 对照组 / 主要终点 / 评估时点 / 关键确证研究 / 入组阈值 / 基线 Hb / 网织红细胞比例 / 补救治疗 / 禁用药 / 方案偏离" 等都属于中文临床试验语境原生表达；不出现"受试者招募 / 排除标准之 X / endpoint at week X" 翻译腔。
- **正面**：时间表达"第16周 / 第24周 / 第4/8/12/16周 / 长期安全性随访 / 维持到第52周" 中文化正确；不出现 "24week" 拼接标签。
- **正面**：脚注解释规范："禁止读成零事件 / 无同期对照 / 公开 vs 未公开" 医学经理一眼懂。
- **小问题（Polish）**："EASI ≥ 75%改善" 中文运算符紧凑（c-09 / c-12）；"中国未核实" 措辞生硬但合规（a-15）；"巴瑞替尼治疗组"旁未说明小绿点（a-08 / a-10）。

### 信息层级与密度

62 页中：
- 4 张封面 + 3 张谢谢（封面/结束页允许留白）— PASS
- 3 张目录 + 3 张首页摘要 — PASS
- 6 张疗效柱图（a-07 至 a-11 + b-04）— a-07 / a-09 / a-10 / a-11 / b-04（修复后）/ b-05（纵向） 大部分 PASS；a-08（小绿点）+ b-04（1.8 不可见） P1
- 4 张矩阵气泡图（a-13 / a-14 / b-07 / c-04）— a-13 / b-07 Polish（横轴留白），a-14 P1（引线空隙）
- 3 张安全性热图（a-12 / b-06 + c 类分散披露状态）— a-12 / b-06 P1（0.0 vs 未公开色块边界不足）
- 30+ 张 B/C 类表格 / 卡片页 — **约 18 张呈现"系统 under-fill"**，占 B/C 类约 42%。

### 图表与表格可读性

- **柱图**: a-07 / a-09 / a-11 节奏好；a-08（小绿点）+ a-10（横轴头距大）+ b-04（y 轴头距大、1.8 不可见）需修。
- **折线**: b-05（纵向）节奏好。
- **气泡**: a-13 / b-07 横轴头距大；a-14 引线空隙 P1。
- **热图**: a-04 / a-05 / a-12 / b-06 / c-17 节奏可；a-12 / b-060.0 vs 未公开色块边界 P1。
- **表格**: B/C 类表格页大部分节奏可；底部留白系统偏大是同一病因。

### 标签归属- 橙色 = 治疗组 / 蓝色 = 对照组 / 红色梯度 = 已公开事件率 / 米色 = 未公开 / 橙色 pill = 已公开 / 灰色 pill = 未公开 —全部归属清晰，**除 a-06 图例 "对照组" 死图例外**。
- 引线 → 气泡 → 标签三向归属在 a-14 上失败（30–50 px 间隙）；其余气泡图引线归属正确。

### 视觉节奏与跨页一致性

- 顶部 chrome（左上橙黄斜切 + 顶线 + 标题 + 右上 Logo）**62/62 一致**。
- 页脚（左 `产品中心-医学部｜2026年X月` + 右 `N / TOTAL` 橙色）**62/62 一致**。
- 标题字号、卡片圆角、阴影、表头色 — 一致。
- 颜色 token（橙 #FF9900、黄 #FFCC00、风险红 #C00000、正文灰 #404040 / #595959 / #808080）— 一致。
- 不出现冷蓝 / navy 默认主调，符合 §0.8.3。
- 主 CTA / RACI 微标 / chip 文字对比达标。

---

## 7. PASS/REVISE advisory（仅建议，非终验）

### PASS / REVISE 总结

| 视口 | 评审 | 说明 |
|---|---|---|
| Chromium 1920×1080（62 页全量） | **REVISE** | 16 P1 缺陷，3 P2 移交问题已确认，多个 P2/P3 polish 项；**未发现 P0**；主因是图表归属（a-06 / a-14）、0.0 vs 未公开色差（a-12 / b-06）、以及18 张 B/C 页的系统 under-fill。 |
| Chromium 1280×800（抽检 12 页 + 全部 flagged-risk） | **REVISE** | 与 1920×1080 同 P1；未出现新 P1。 |
| Chromium 2048×1024（抽检 4 页 + flagged-risk） | **REVISE** | 与 1920×1080 同 P1；a-14 引线空隙因画布拉伸被夸大；under-fill 因等比居中留白更明显。 |
| WebKit 1920×1080 | **未审（scope gap）** |三个 WebKit subagent 被取消；个人未直接检视 WebKit originals。Codex /后续代理需要补做 WebKit 全量原始图像视检以完成四视口双浏览器闭环。 |

### 优先级修复建议（给 Codex 修复阶段）

1. **P1-1 (a-06)**：删除"对照组"图例或重画分组柱形 — 单页可修复。
2. **P1-2 (a-12) / P1-6 (b-06)**：0.0 已公开格加深1 色阶 — 全 deck 共用色板，可批量修。
3. **P1-3 (a-14)**：引线终点延至紧邻文字 — 单页几何修正。
4. **P1-5 (b-04)**：y 轴 0–95 + 1.8 数值标签加粗 + APPOINT-PNH 加注释 — 单页可修。
5. **P1-4 / P1-7 至 P1-14 / P1-15 / P1-16（B/C 类 under-fill）**：建议优先抽 6 张重点页（b-16筛败、b-17 补救、b-22 档案、c-15 路径一、c-16 路径二、a-19 局限）做内容增补，证明 under-fill 可治理；其余 12 张按相同模式批量套用。
6. **P2-1 / P2-2 (c-09 / c-12)**："EASI ≥ 75%改善" 加半角空格 + NCT 号移到副行 — 单页可批量修。
7. **P2 (a-08 / a-10 巴瑞替尼小绿点)**：删除或加图例 — 单页可修。
8. **P2 (a-13 / b-07 气泡图横轴头距)**：x 轴动态区间 — 几何修正。

### WebKit 闭合建议

在完成上述 P1/P2 修复后，必须由 Codex 或后续 reviewer 在 WebKit 内核下重新采集 62 张原图并按本报告框架逐页视检；本会议已声明的 WebKit 缺位需补做。

### 我作为医学经理的最终意见（advisory only）

62 页整体已具备"医学经理快读"所需的中文原生表达、证据完整性与图表归属清晰度；但 a-06 / a-14 / a-12 / b-04 / b-06 五张核心信息页存在**会让我在 30 秒快读路径上停顿 ≥ 2 秒**的归属或可读性缺陷，而 B/C 类约 18 张内容页的下半页留白会让医学经理产生"未完成"的整体印象。

Codex 修复上述16 个 P1 + 3 个 P2 移交问题后，可以进入最终视觉终验与 run manifest 锁定。我不替代 Codex 的终验权，本报告仅为独立医学经理视觉建议。

---

**Role marker**: minimax-medical-manager
**Inspected**: Chromium 1920×1080 × 62 originals (all 62 ids); Chromium 1280×800 × ~12 originals (flagged-risk + sample); Chromium 2048×1024 × ~4 originals (flagged-risk); WebKit 1920×1080 — **NOT inspected personally** (acknowledged scope gap).
**Returns to Codex**: this inline report (no runner-managed output file was written; per conference contract).
