Confirmed — at 1920 webkit the C design-map "设计事实比较" table is **completely garbled**, every row's Chinese text overlapping the row above and below. The "主要终点与评估时间" (endpoint-timepoint-matrix) page has the same defect: "IGA达到0或1分" appears ~20 times stacked on top of each other. These are P0 visual failures of the C report at 1920 webkit.

I have sufficient evidence. Now writing the final review report.

---

# Visual Review: named_pi_minimax

报告人: `named_pi_minimax`，身份: 资深临床试验医学经理（视觉敏感、不耐烦工程术语、要立刻看出比较）
模式: 仅审阅，不修改任何产物；本回复为正式视觉验收报告（runner-managed 路径 `runs/conference/ci-phase10-task102-visual-review/named_pi_minimax.md`）。

## Boundary Check

- 仅读取 `context/ci-phase10-task102-visual-review_conference_context.md`、`contracts/kangzhe/design_specs/project_profile.md`、`plans/codex_main_venue_ci-phase10-task102-visual-review.md`。
- 仅读取 `task-10.2-20260901-123524/{a-real,b-real,c-real}/verification/{A,B,C}/v1/` 下的 PNG截图与 `report.json`，未触碰任何源文件、证据、报告、外部状态、未公开页面生成目录。
- 使用 `read` 直接读取 PNG；未以文件名或 HTML 源推断外观。
- 未调用任何写工具；报告正文返回于本回复。

## Inspected Evidence

实际打开的截图（浏览器 × 视口 × 页面）：

A（特应性皮炎） — `a-real/verification/A/v1/screenshots/`：
- `a_overview__chromium__1280x800.png`、`a_overview__chromium__1920x1080.png`
- `a_overview__webkit__1280x800.png`、`a_overview__webkit__1920x1080.png`
- `a_efficacy__chromium__1280x800.png`、`a_efficacy__chromium__1920x1080.png`、`a_efficacy__webkit__1280x800.png`
- `a_safety__chromium__1280x800.png`、`a_safety__chromium__1920x1080.png`、`a_safety__webkit__1280x800.png`
- `a_matrix__chromium__1280x800.png`、`a_matrix__chromium__1920x1080.png`、`a_matrix__webkit__1280x800.png`、`a_matrix__webkit__1920x1080.png`

B（阵发性睡眠性血红蛋白尿） — `b-real/verification/B/v1/screenshots/`：
- `b_overview__chromium__1280x800.png`、`b_overview__chromium__1920x1080.png`、`b_overview__webkit__1280x800.png`、`b_overview__webkit__1920x1080.png`
- `b_efficacy-safety-matrix__chromium__1280x800.png`、`b_efficacy-safety-matrix__chromium__1920x1080.png`、`b_efficacy-safety-matrix__webkit__1280x800.png`、`b_efficacy-safety-matrix__webkit__1920x1080.png`
- `b_baseline-overview__chromium__1280x800.png`、`b_baseline-overview__chromium__1920x1080.png`
- `b_baseline-demographics__chromium__1280x800.png`、`b_baseline-demographics__chromium__1920x1080.png`
- `b_disposition-overview__chromium__1280x800.png`、`b_disposition-overview__chromium__1920x1080.png`

C（中重度特应性皮炎设计比较） — `c-real/verification/C/v1/screenshots/`：
- `c_overview__chromium__1280x800.png`、`c_overview__chromium__1920x1080.png`、`c_overview__webkit__1280x800.png`、`c_overview__webkit__1920x1080.png`
- `c_design-map__chromium__1280x800.png`、`c_design-map__chromium__1920x1080.png`、`c_design-map__webkit__1920x1080.png`、`c_design-map__webkit__1920x1080.png`
- `c_endpoint-timepoint-matrix__chromium__1280x800.png`、`c_endpoint-timepoint-matrix__chromium__1920x1080.png`、`c_endpoint-timepoint-matrix__webkit__1280x800.png`、`c_endpoint-timepoint-matrix__webkit__1920x1080.png`
- `c_trials_nct02260986__chromium__1280x800.png`、`c_trial-profile__chromium__1280x800.png`

`report.json` 仅记录 `ok / violations`，未记录图表横向溢出与单元格行高数据；以下缺陷以截图直接判断。

## Medical-manager Findings

逐页现场感受（先说感觉，再定位缺陷）：

- A 类「创新治疗格局与医学结果」首屏清晰：靶点 × 候选药矩阵一目了然，橙色主色与桔色胶囊一致，标题层级符合临床阅读习惯。这条线是三份报告中唯一在首屏就能直接读出"竞品格局"的。
- A 类「疗效」页：柱状图按"治疗组 vs 对照组"成对显示且附百分比标签，柱底标签清晰；左侧筛选器（产品 / 时间窗 / 主要终点）层级合理。
- A 类「安全性」页：颜色从浅黄到深红递进、每格直接印百分比，密度合适；但首屏无颜色图例，须向下滚动才知道颜色对应的 SAE/AESI/常见 AE 维度。
- A 类「疗效及安全性矩阵」气泡图：气泡本身仅标注 `1, 2, 3…`，产品名挪到下方图例 —医学经理必须眼动跳转。这是规范明确不接受的。
- B 类「首页」关键结果图：首屏只渲染了 1根治疗组柱（82.3）与1 根极矮对照组柱（2），可视化面板几乎全空，浪费首屏空间且误导（看不出"竞品比较"）。
- B 类「试验完成情况」首屏 Y 轴标题"相对剂量强度"压在最高数据标签 "125" 上，与图表数据互相覆盖。
- B 类「疗效与安全性矩阵」首屏：仅显示一个 APPOINT-PNH 数据缺失的橙色 callout 与空轴线；气泡一个都没画。
- C 类「首页」「设计图谱」「终点、定义与时间点」三页的比较表在 1280 和 1920、Chromium 与 WebKit 均出现同一严重故障：每一行中文文本与上一行、下一行直接叠加，行与行之间没有视觉分隔、行高明显小于两行中文所需高度。第一屏完全无法阅读。
- C 类「试验详情 (NCT02260986)」是 C 报告中唯一排版正常的页面：4 列卡片"目标人群 / 给药方案 / 主要终点定义 / 计划或实际样本量"清晰可读。
- A/B/C 顶部导航结构差异：A 8 项首屏收纳为"菜单"折叠 +6 个直接项；B 5 项直接展示且对"首页"叠加橙色下划线高亮（暗示当前是首页，符合期望）；C 5 项直接展示且对当前页加橙色下划线。视觉一致性上 A/B/C 不一致：A 顶部"更多"折叠对资深医学用户不友好。

整体语言、术语、单位全部为中文原生，未出现 `gate / signal / accepted / registry-only / run_digest / evidence engine` 等后端字段或日志词。

## Defects And Remediation

| # | 页面 / 视口 | 缺陷 | 严重度 | 修复建议 |
|---|---|---|---|---|
| D1 | C 「首页 / 设计图谱 / 终点、定义与时间点」所有视口 × 两个引擎 | 比较表 body 行内中文段落与相邻行严重叠加；肉眼完全无法读出任何一行；表格行高< 两行中文所需高度，无 row separator 与背景色差 | P0 | 表格 `tbody tr` 设 `line-height: 1.6+`、`padding-block: 12px+`；超过1 行的 cell 设 `min-height: 56px`；增加交替行底色或 `border-bottom: 1px solid`；可滚动容器保持 |
| D2 | C 「设计事实比较」1920 webkit | 同 D1，且横向出现 `target_population / inclusion_criteria / randomisation / arms / …` 这种英文斜置列脚标 —不可读 | P0 | 删除英文小字列脚标，全部用中文列名；并复检是否英文 UI 文案混入 |
| D3 | A 「疗效及安全性矩阵」1280 与 1920，Chromium 与 WebKit | 气泡图只用序号 `1, 2, 3…` 标注；规范要求"气泡图必须直接说明横轴、纵轴和气泡大小对应的临床变量"，且医学经理必须看到产品名才能判断 | P1 |气泡内部或紧邻气泡直接显示产品名（或试验代号）；如空间不够则放试验代号，详见下方 Legend 与气泡 ID 对照 |
| D4 | B 「首页」关键结果图 1280 × 1920 | 首屏图表面板80% 空白；只看到一组"治疗组 82.3 / 对照组 2"的孤柱；规范要求"图在前、完整表格在后"，但首屏无法传递竞品比较 | P1 | 默认入参至少展示每个竞品（5 个）的首位主要终点成对柱；并把"未公开"列到右栏；不要只取唯一试验唯一终点 |
| D5 | B 「疗效与安全性矩阵」1280 | 首屏只看到一个 APPOINT-PNH "TEAE 总数未公开" callout 与空白轴；0 个气泡渲染 | P1 | 默认筛选移除会清空气泡的试验，或绘制含 "未公开" 标识的占位气泡并就近注释；图例须先于空轴出现 |
| D6 | B 「试验完成情况」1280 × 1920 | Y 轴标题"相对剂量强度"与最高数据标签 "125" 在同一像素层重叠 | P1 | Y 轴标题移到最左侧独立列；或在最高柱之外加 padding-top ≥ 24px |
| D7 | A 顶部导航 1280 / 1920 两个引擎 | A 顶部 8 个入口中1 个被折叠到"更多"，且"菜单"按钮与"更多"并存；医学经理不熟悉"菜单"按钮含义 | P1 | 顶部一级导航精简为5–6 项；或者把"更多"改为"全部页面"并加可识别图标，避免同时出现"菜单"与"更多"两个冗余控件 |
| D8 | A 「安全性」1280 首屏 | 颜色深浅图例（SAE/AESI/常见 AE 颜色映射）不在首屏；用户不知颜色意义 | P2 | 把图例放到首屏紧贴热图上沿，或在热图标题处加可点击"图例"按钮弹层 |
| D9 | A 「疗效」1280 webkit | 最末一行"来布利珠单抗"对照组柱部分被卡片底部裁切 | P2 | 卡片底 padding 加16px+，或柱条 max-height 限制并允许垂直滚动容器 |
| D10 | B 基线与人群总览 1920 chromium | X 轴长标签（如"基线样本量治疗组"）在柱下换行后被裁切 | P2 | X 轴标签允许2 行 + 旋转 ≤30°；或拆分多个 panel |
| D11 | B 「基线与人群总览」所有视口 | 顶部块标题"基线与人群总览" 与 全局页标题完全重复（红色 / 黑色） | P2 | 改为区段标题「关键基线与人群特征」之类，与页面 H1 区分 |
| D12 | C顶部导航 1280 / 1920 | 当前页的橙色下划线位置正确，但 B 与 A 的当前页指示不一致：A 顶部用"菜单"折叠导致"竞争格局"等当前状态对不可见；B 用下划线 + 加粗；C 单独下划线。 | P2 | 统一三套顶部导航的当前页指示样式（建议：下划线 + 字重 + 主色） |

确定性 vs 主观视觉验收：

- D1 / D2 / D6 / D9 / D10：可在原始 PNG 上肉眼直接观察，属于"肉眼可拒绝"硬性视觉缺陷（重叠/裁切）。
- D3 / D4 / D5：构图缺陷，可在原始 PNG 上观察，属于硬性视觉缺陷。
- D7 / D8 / D11 / D12：信息架构与一致性，主观判断 + 仍属视觉可拒绝。

确定性硬性视觉缺陷集合 = {D1, D2, D6, D9, D10}；其余主观判断。

## Verdict

- **A 类**：单页硬性视觉缺陷极少（D9 仅一处底部裁切）。但 D3 气泡无产品名、D8 安全图例不在首屏是医学经理会立即感到不便的可用性问题。**视觉验收：先放行主体、放行前必须修复 D3 / D8 / D9 三项**；D7导航折叠顺带处理。
- **B 类**：首屏可用性差（D4 空图、D5 空气泡、D6 轴标题压数据）。**视觉验收：拒绝放行**，须修 D4 / D5 / D6 与 D11、D10 后重新跑视觉验收。
- **C 类**：核心比较表（D1 / D2）在所有视口与两个引擎下严重叠加，首页 / 设计图谱 / 终点时间点三页的首屏比较表完全不可读。**视觉验收：拒绝放行**，须修 D1 / D2 与 D12 后重新跑视觉验收。C 的试验详情单页可用，但不能掩盖三页核心比较表全部失败。

整体判定：

- **P0 视觉缺陷未关闭**：C 全套设计比较页表格（D1 / D2）。
- **P1 视觉缺陷未关闭**：A 矩阵气泡（D3）、B 首页图（D4）、B 矩阵图（D5）、B 完成情况 Y 轴（D6）、A 顶部菜单（D7）。
- **结论：不做总体放行。** A 在修 D3 / D8 / D9 / D7 后可单线放行；B 与 C 须返工修复后再次提交视觉验收；不允许以截图文件存在、退出码 0 或 `report.json` `ok=true` 替代真实肉眼视觉验收。
