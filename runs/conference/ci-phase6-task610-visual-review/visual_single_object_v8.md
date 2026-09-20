# Conference Participant Output: ci-phase6-task610-visual-review - visual_single_object（v8 定向复核轮）

## Boundary Check

- 仅只读复核 `output/acceptance/task-6.10/b-pnh-current-v8/reports/B/v-fixture-b-pnh-001/html/`；本地 HTTP 服务（hub 进程 `v8site`）复核后已停止；未修改任何文件，未读其他审阅者输出，未做最终验收。
- 引擎：真实 Chromium（xd://browser，1024×800）+ 真实 WebKit 26.4（Playwright `webkit-2287`，1024×800）。WebKit 可用，无需声明工具缺失。
- 对照真源：`fixtures/positive/b-pnh/inputs/report-data.json`（只读复算）。

## Independent Work Product

### 三项修订的定向复核结果

**修订 1（基线小多图）— 通过，双内核实证。**
- `baseline-demographics.html` 现渲染 4 张 SVG 小多图，各自标题含单位："基线样本量｜基线变量（人）""年龄｜基线变量（岁）""性别｜基线变量（%）""基线血红蛋白｜基线变量（g/dL）"；每张轴标签仅含本单位（人/岁/%/g/dL），轴刻度各自适配（0–60 / 0–50 / 0–100 / 0–8+）。同一数值轴不再混合不可比单位，P1-V1 关闭。数值与 fixture 逐点一致（62/35/40 人；51.7/49.8/42.1 岁；69.4/68.6/42.5%；8.9/8.9/8.2 g/dL）。WebKit 截图渲染与 Chromium 一致。

**修订 2（字号 ≥16px）— 大部分通过，有一处残留 P1。**
- 在 Chromium 上轮 13 个页面（含全部基线/处置/疗效/安全页）实测可见叶节点文本 <16px 计数 = 0；页眉元信息、页脚、轴标签、数值标签均已 ≥16px。
- **残留缺陷 P1-V2r**：`.kz-chart-undisclosed` 占位组件仍为 14px（`__title`："产品与试验属性按完整字段表列示，图形不适用于此页"）和 **13px**（`__hint`："完整记录仍列于下方表格，便于核对来源与口径。"）。复现路由（Chromium 与 WebKit 双双复现）：`product-trial-profiles.html`、`trials/nct04820530.html`、`evidence-limitations.html`。这两段是可见正文段落，非表体/轴标签，无 `data-density=ultra` 例外通道，违反 core.md §0.7 site_html 16px MUST 下限（13px 还触及"NEVER < 13px"边界的语义灰色区）。
- 最低修复：该组件两级文字统一升至 16px（改动单点、无重排风险）。修复后复测 = 全 24 页 <16px 可见文本计数归零。

**修订 3（处置按试验拆图、仅绘已报告值）— 通过，双内核实证。**
- `participant-flow.html` 现有 2 张图："APPLY-PNH · 试验完成情况"与"APPOINT-PNH · 试验完成情况"；数值标签逐个分离可读（120/62/62/62/62/60/60/59/59），上轮"6262626260605959"粘连消失；类别+组别双行轴标签视觉分层干净（机器检测的残余"重叠"为相邻行文本边界盒贴边的假阳性，截图目检无碰撞）。
- 缺失处理正确：APPLY 图中无"筛选失败"柱（fixture `screen_failure = not_publicly_disclosed`），SVG 内仅有的两个 "0" 文本均位于 y 轴原点（x=153 轴槽），无零值冒顶缺失；`已报告零值` 出现 0 次、未公开行仍 120 处完整保留在下方表格。图—表身份同步：图"已筛选/全研究人群" ↔ 表首行"已筛选｜全研究人群｜筛选至第24周｜全登记人群｜已报告值"。

### WebKit 1024 补充轮

- 24/24 页面 `scrollWidth − clientWidth = 0`；除上述占位组件外无 <16px 文本；所有含图页面 SVG 正常渲染（`subgroups-supporting-evidence.html`、`product-trial-profiles.html` 等无图页 SVG=0 属预期）。截图证据：`/tmp/wk-baseline.png`、`/tmp/wk-flow.png`、`/tmp/wk-safety.png`。
- Chromium 24 页横向溢出同为 0（本轮复扫 13 页 + 上轮基线，另 11 页 WebKit 侧补验）。

### 新提请注意（非门户缺陷）

- **fixture 内部张力 [INFERENCE→需 Codex 裁定]**：`disposition_views` 中 APPLY-PNH `randomized apply-control = 62`，而 `safety` 对照组安全性分析集分母 = 35。真实 APPLY-PNH 为 62:35 随机。门户两处均忠实渲染 fixture，但医学经理会在"已随机 对照组 62"与"对照组 35"之间发现矛盾。属数据真源问题，超出本视觉角色修订范围。

## Evidence And Assumptions

- 实测证据：Chromium 实时求值（字号直方图、SVG 文本/刻度抽取、零值定位、重叠边界盒）；WebKit 24 页脚本化扫描输出"BAD PAGES"仅含占位组件字号项；截图 5 张（临时目录，报告内已嵌描述）。
- 静态证据：fixture `baseline_views.facts` / `disposition_views.facts` 逐行核对。
- 假设：占位组件 14/13px 在 v8 其余页面不存在（Chromium 13 页 + WebKit 24 页交叉覆盖，置信高）；fixture 数值张力不视为本轮渲染缺陷。
- 未变更结论：上轮其余通过项（中文原生、缺失语义、交互恢复、热图/气泡图）本轮未复测，假设 v8 修订未触碰这些路径 [INFERENCE]。

## Risks, Gaps, And Verification Needs

- P1-V2r 是合同 MUST 项的最后残留，修复前字号地板条款无法勾销；修复面为单组件两级文字，风险极低。
- 未覆盖：200% 缩放与键盘焦点全量、1280/1440 的 WebKit 轮（仅 Chromium 有上轮 1280/1440 数据；v8 若引入新版式建议补一轮 Chromium 1280/1440 快扫）。
- 对 Codex 的有界问题：fixture `randomized apply-control=62` 是否有意（若有意，建议在处置页口径提示列注明"随机化人群与安全性分析集分母不同"）？
- 程序性挑战：上轮"字体全站已 ≥16px"的修复声明在占位组件上漏网，说明 Codex 侧修复验证用的是页面子集；建议把"<16px 可见文本计数"加入机器验收门禁（24 页全量、双内核），防止同类残留再次漏网。

## Recommended Next Step

1. 单点修复 `.kz-chart-undisclosed__title/__hint` → 16px，全 24 页 <16px 可见文本计数归零即复测通过（改动极小，可直接进 v9 或就地修订后复核）。
2. Codex 裁定 fixture 62 vs 35 随机对照组数值；若保留，补口径提示文案。
3. 上述两项关闭后，本角色对 v8 修订的三项复核全部通过，无其他 P0/P1；可将"<16px 文本计数"与"SVG 零值冒顶检测"纳入最终验收门禁脚本，随后进入 Codex 终验。
