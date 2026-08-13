# Task Context: ci_phase4_task44

Created: 2026-08-14 04:47:03
Objective: 实现 ECharts 图形注册、兼容性判定、小多图拆分、完整表及图表筛选联动
Task type: `html_ppt_visual_browser`
Risk: `high`
Selected agent route: `alibaba` / `qwen3.8-max` / `xhigh`

## Trigger Reason

This task was initialized through the Codex x Hermes complex-task entrypoint because it is expected to involve more than three execution steps, research/writing/report/code/report-visual work, or source-grounded verification.

## Source Of Truth

- 批准实施计划 Phase 4 Task 4.4：`/Users/smkzw/Documents/AI Products/.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md` 第 900 行起。
- 设计 v1.2 的图先表后、全量表、动态筛选与可比性原则：`docs/specs/competitive-intelligence-workflow-design-v1.2.md`。
- 已冻结技术路线：`docs/decisions/0001-technology-stack.md`、`docs/decisions/0003-offline-presentation-assets.md`；Apache ECharts 6.1.0 已入包，不重新选型。
- 已接受 Task 4.1 单一行集合合同：`src/ci_workflow/reports/common/chart_specs.py`、`view_state.py`。
- 已接受 Task 4.3 分层筛选与网址状态：`src/ci_workflow/renderers/portal/{filters,url_state,page_shell}.py` 与门户资源。
- 康哲项目内化设计合同：`contracts/kangzhe/design.md`、`contracts/kangzhe/design_specs/`。

## Scope

- In scope：柱状图、折线图、森林图、热图、气泡图、点图/区间图、时间线、雷达图、状态矩阵的类型化输入合同与注册。
- In scope：单位、量表、统计形式、方向、时间窗、分析人群、组别/对照及分母等可比性判定；不兼容记录必须确定性拆成带清楚中文标题的小多图，不能丢弃或补造值。
- In scope：离线 ECharts 渲染；图在前、完整表在后；图形点/系列选择与表格高亮/筛选同步，二者 row ID 集合恒等，并继承 Task 4.3 状态。
- In scope：缺失、未公开、不适用、未达到展示条件用非数值状态保留；不得把缺失转 0 或为了画图估算。
- Out of scope：Task 4.5 证据抽屉、A/B/C 完整业务页面、PDF/PPT、真实临床结论、安全专项测试。

## Success Criteria

- 九类图形均有明确的字段要求、支持/拒绝原因和中文显示合同；未知图形或自由文本类型失败关闭。
- 同一可比组内维度一致；有任何关键维度不一致时按最小必要维度拆分小多图，拆分结果稳定且所有原始行恰好出现一次。
- 默认图形不以综合评分或隐含排序误导：疗效方向、对照效应和安全性“发生率越低越有利”等语义由显式字段/标签承载。
- 图和完整表只从同一 `FilteredRowSet` 派生；任意筛选、图上点选或恢复后，两侧 row ID 完全一致，空结果不扩围。
- 页面离线运行且不请求 CDN；1280/1024 下图、图例、控制项和表格无重叠、截断或程序员/日志文案。
- RED 反例和 GREEN 实现均可复跑；最终全库、Ruff、strict mypy、包校验与真实 Chromium/WebKit 浏览器测试通过。

## Risk Boundaries

- 允许写入仅限 Task 4.4 计划文件列出的源文件、`assets/portal/charts.js`、对应测试及生成的任务内截图/证据；不得改已接受设计合同或任务计划。
- 不因图形不兼容删除药物/试验/行，不把“未公开”显示为 0，不以图能出现作为科学可比性的证据。
- 不把 ECharts option 当科学真源；option 只消费类型化、锁定快照绑定的规范行与显示值。
- The delegated agent is not final authority; Codex owns verification and acceptance.

## Timeout Policy

- Do not mark the delegated agent failed for slow response alone.
- For complex or artifact-heavy work, wait and poll generously; use conference mode when multiple independent model perspectives are needed.
- Failure requires terminal error, provider exhaustion/rate limit after controlled retry, empty/truncated retry output, or no progress after hard wait plus one retry.
- A provider catalog/auth/transport preflight is diagnostic, not a live capability verdict: timeout, auth refresh failure, malformed output, or a stale/incomplete catalog must be recorded and followed by one real route attempt. Explicit user-selected routes are not blocked merely because the catalog does not list them; only a missing executable or native transport boundary may stop before that attempt.

## Loop Log

- 2026-08-14 04:47:03: Task initialized by `tools/hermes_workflow_guard.py init-task`.
- 2026-08-14 04:48: Codex 复核已采用 ADR；外部方案扫描无需重开，ECharts 6.1.0 的来源、许可证、离线运行与组件覆盖已在 Phase 0 决策和真实浏览器证据中冻结。当前方法选择只需针对任务合同做反例驱动实现。
- 2026-08-14 06:30: 首轮确定性实现达到 102 项图形合同、42 项双浏览器合同；执行经理在原会话修复了 Python 分组与 fixture 漂移、九类图伪回退、ECharts 未入正式构建链和 pointer API 兜底。
- 2026-08-14 06:32–07:04: 三条用户指定视觉路线进行真实医学经理试用。CodeBuddy/kimi-k2.6 与 Pi/minimax-m3 均否决首版：筛选浮层落到页底、URL 状态不保留、未公开占大空图、负值柱误读、组别/数值不可一眼读取。Grok Build 产生首轮截图并给出同类否决。
- 2026-08-14 07:05–07:31: 原 Worker 03 同会话完成修复；Codex再补“指标名｜口径”标题和负值柱内标签。CodeBuddy 与 Minimax 修复后复验均在 fixture 边界 PASS；Grok Build 两次同会话复验只返回准备语且无新证据，按无进展规则排除，不将其算作通过。
- 2026-08-14 07:32: Codex 独立检查修复后真实截图；245 项聚焦套件、851 项全库、scoped Ruff、strict mypy、包校验与 diff 检查通过。Task 4.4 接受；下一项 Task 4.5。
