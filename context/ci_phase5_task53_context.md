# Task Context: ci_phase5_task53

Created: 2026-08-17 23:27:04
Objective: 内化最新版康哲设计合同并实现A类疗效、安全热图与疗效—安全气泡矩阵数据合同
Task type: `competitive_intelligence`
Risk: `high`
Selected agent route: `codex` / `codex-main` / `high`

## Trigger Reason

This task was initialized through the Codex x Hermes complex-task entrypoint because it is expected to involve more than three execution steps, research/writing/report/code/report-visual work, or source-grounded verification.

## Source Of Truth

- `docs/specs/competitive-intelligence-workflow-design-v1.2.md` §12.2–12.4、§15.2–15.7。
- `../.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md` Task 5.3。
- `contracts/kangzhe/design.md → design_specs/{ROUTER,core,project_profile,track_site}.md`；本次已从 `kangzhe-design` v3 稳定包内化并由提交 `3492a6b` 固化。
- Task 5.1/5.2 已接受的 `src/ci_workflow/reports/a/{contracts,analysis,pages}.py`、提交 `8b02185` 与 `9be2ea3`。
- Phase 3 已锁定的 `ApplicableUniverseSnapshot`、`GateEvidenceBinding`、不可变事实与来源定位合同。

## Scope

- In scope：Task 5.3 的强类型只读分析模型；确定性锚定试验；按靶点分组的疗效治疗组/对照组比较；保留事件、时间窗、分母和披露状态的安全性热图；疗效—安全性气泡矩阵及半径公式；当前快照、全产品、证据定位与内容摘要闭合。
- Allowed outputs：`src/ci_workflow/reports/a/analysis.py`、`src/ci_workflow/reports/a/__init__.py`、`tests/reports/a/test_efficacy_safety_summary.py`、`tests/reports/a/test_bubble_matrix.py`、本任务记录与 Phase 5 Trellis 文件。
- Out of scope：HTML/模板/浏览器页面、PDF/PPT、真实来源抓取、B/C 报告、安全专项测试；视觉医学经理试用留到 Task 5.4/5.5 有真实页面后执行。

## Success Criteria

- 默认锚定只从本产品当前快照中的适格核心/特殊核心试验选择，顺序只使用试验角色、阶段、披露成熟度和稳定试验 ID，不使用疗效或安全数值。
- 疗效视图默认按靶点分组；每项结果保留原始定义、方向、单位、时间点、分析人群、治疗组和对照组数值、分母、试验与事实版本；不得静默池化或生成默认名次。
- 安全性热图至少能表达 TEAE、SAE、AESI 与常见 AE；每个单元保留事件定义、时间窗、组别、分母、报告数值/零或准确披露状态，空白失败关闭。
- 气泡横轴为方向校正后的当前疗效信号，纵轴为倒序原始 TEAE 发生率，面积来自治疗组样本量，半径严格为 `k × sqrt(N/pi)`；固定中文轴提示，不含综合分数或排名字段。
- 所有分析输出绑定当前项目、证据快照、研究角色集、完整产品集及内容摘要；`model_copy` 篡改、跨产品/未知试验、旧快照、缺治疗/对照或缺分母均失败关闭。
- 两个新测试文件先出现精确失败再通过；A 专项、共享证据、全仓非浏览器回归、Ruff、strict mypy与独立反证验收通过。

## Risk Boundaries

- 不从自由文本推断试验角色、终点兼容性、治疗/对照角色或安全事件族；均由封闭枚举和引用当前事实版本的记录表达。
- 不把缺失变成零，不把发生率最高/最低变成“最安全/最危险”，不跨试验自动池化，不默认排序，不生成综合分数。
- 用户可见标签必须为中国临床试验语境的中文原生表达；不暴露工程状态、提示词或日志语言。
- 本任务不生成页面，视觉测试模型将在真实门户产物阶段运行，避免用数据模型冒充视觉验收。
- Codex 是最终接受方；独立审查者只可否决或接受，不能静默改写。

## Timeout Policy

- Do not mark the delegated agent failed for slow response alone.
- For complex or artifact-heavy work, wait and poll generously; use conference mode when multiple independent model perspectives are needed.
- Failure requires terminal error, provider exhaustion/rate limit after controlled retry, empty/truncated retry output, or no progress after hard wait plus one retry.
- A provider catalog/auth/transport preflight is diagnostic, not a live capability verdict: timeout, auth refresh failure, malformed output, or a stale/incomplete catalog must be recorded and followed by one real route attempt. Explicit user-selected routes are not blocked merely because the catalog does not list them; only a missing executable or native transport boundary may stop before that attempt.

## Loop Log

- 2026-08-17 23:27:04: Task initialized by `tools/hermes_workflow_guard.py init-task`.
- 2026-08-17 23:27–23:36: 完整读取最新全局/项目 AGENTS、Trellis 与 `kangzhe-design` v3；纠正门户路线为单一 `site` 主轨。最新分轨合同内化为项目副本，项目合同 9 项结构测试、104 项全合同回归通过，提交 `3492a6b`；后续不再同步通用版。
- 2026-08-17 23:36: 重新读取 v1.2 §12.2–12.4/§15.2–15.7 与计划 Task 5.3，确认本步只实现数据分析合同，不生成页面或做伪视觉验收。
- 2026-08-17 23:44–2026-08-18 00:02: 两个 Task 5.3 测试文件先因新合同尚不存在而精确失败，随后完成强类型实现。汇总绑定完整产品集、快照、研究角色集、事实版本与内容摘要；比较设计强制保留治疗组/对照组；早期产品无公开结果仍保留；热图将人数按分母换算为发生率后着色并保持原始值/缺失态；气泡只取确定性锚定试验，默认治疗期间不良事件发生率，半径采用治疗组安全性分析集分母。
- 2026-08-18 00:02: Task 5.3 定向 12 项、A 类专项 322 项、全仓 1346 项全部通过；Ruff 与 `mypy --strict` 通过。全仓回归用时 570.23 秒。
- 2026-08-18 00:03: 按最小多节点原则启动全新上下文的 Luna 独立反证审查；原先初始化但未派发的双会场脚手架已清理，避免把未运行会商记录留作验收证据。Task 5.3 无页面产物，因此 minimax/Grok 视觉医学经理试用保留到 Task 5.4/5.5。
- 2026-08-18 00:10–01:05: Luna 连续三轮以新反例否决“测试全绿”。修复内容包括：TEAE/SAE 不得互换、已报告数值必须有正分母、比较设计安全性不得丢对照、原始疗效定义/方向保留、锚定候选逐试验闭合、人数换算率可用于气泡、完整快照摘要绑定；随后进一步补齐旁路模型重验、强类型组别角色、阶段事实、终点/时间点/分析集兼容、百分比与人数范围、多臂组别闭合、总体治疗期间不良事件默认定位及气泡事实追溯。
- 2026-08-18 01:06: 第四版定向 34 项、A 类合并 344 项通过；Ruff 与 strict mypy 通过。第三次全仓回归在上一轮修复后为 1360 项通过；当前统一强输入合同正在由同一 Luna 会话复验，最终全仓回归待独立验收通过后再执行一次。
- 2026-08-18 01:06–02:19: 同一 Luna 独立会话继续以真实反例审查，不因已有绿测停止。最终闭合：设计事实权威组名、单臂/比较设计组别数量、全部终点族快照归属、疗效方向封闭白名单、全部已接受结果映射、监管材料结果与产品层监管背景区分、安全性单位及数值范围、完整安全性语境唯一性、未量化语境不被静默过滤、气泡摘要回填实际事件/定义/时间窗/分析集、无效筛选拒绝及组级不可绘制说明。
- 2026-08-18 02:19: Luna 最终独立结论 `PASS`，P0/P1/P2 均为 0；未修改项目文件。定向 53 项、A 类组合 363 项、Ruff、strict mypy 与 `git diff --check` 均通过。
- 2026-08-18 02:20–02:27: 最终全工程 `uv run pytest -q` 完成，1387 项全部通过，用时 423.21 秒。Task 5.3 不含页面，因此未调用 minimax/Grok 做伪视觉验收；Task 5.4/5.5 生成真实可操作门户后再按真实医学经理角色执行视觉端到端试用。
- 2026-08-18 02:28: Trellis、上下文、指标和独立审查记录已固化；下一安全动作是 Task 5.4，先读取本文件、实施计划 Task 5.4 与项目内化的 `design_specs/track_site.md`，不得重做 Task 5.3。
