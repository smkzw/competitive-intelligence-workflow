# Execution Context: ci_phase4_task44_execution

Created: 2026-08-14 04:47:45
Objective: 按 Task 4.4 实现可比性驱动的九类图形注册、小多图拆分、完整表及浏览器联动
Task type: `html_ppt_visual_browser`
Risk: `high`
Execution module trigger: Codex identified 3 independent work items, which is greater than two.

## Module Boundary

This is an execution module, not a conference. Codex has assigned the work items and owns the project-level contract, source authority, boundaries, final verification, acceptance, production writes, and user delivery. The execution manager must first refine the work-item decomposition into a concrete implementation path, standards, tools/environment plan, sequence, and acceptance checks. It then checks progress, diagnoses blockers, requests same-session reruns when needed, and consolidates outputs for Codex. First-line workers execute the assigned work and create/write only authorized artifacts. Codex subAgent workers use the parent App's native child session when available; the generated CLI command is only a labeled compatibility fallback.

## Assigned Roles

- First-line executor: `visual_executor_pi_qwen38` -> `pi` / `alibaba` / `qwen3.8-max`
- Execution manager: `visual_manager_cursor` -> `cursor` / `cursor-cli` / `auto`
- Execution-manager fallback: `Codex takes over execution management directly`

## Source Of Truth

- `context/ci_phase4_task44_context.md`：项目级目标、来源、范围、验收与已冻结技术路线。
- `/Users/smkzw/Documents/AI Products/.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md:900`：Task 4.4 唯一实施步骤。
- `docs/specs/competitive-intelligence-workflow-design-v1.2.md` 与 `contracts/kangzhe/design.md`：产品与视觉合同。
- `src/ci_workflow/reports/common/{chart_specs,view_state}.py`：Task 4.1 已接受行集合边界。
- `src/ci_workflow/renderers/portal/{filters,url_state,page_shell}.py` 与 `assets/portal/`：Task 4.3 已接受筛选/网址运行层。
- `assets/third-party/echarts/`、`docs/decisions/0001-technology-stack.md`、`0003-offline-presentation-assets.md`：已固定的 ECharts 6.1.0 离线资产，不重新选型或下载。

## Risk Boundaries

- No production writes.
- 允许修改范围仅为 `src/ci_workflow/reports/common/chart_specs.py`、新建 `assets/portal/charts.js` 与对应包内副本（若运行时需要）、门户最小接线、`tests/unit/reports/test_chart_compatibility.py`、`tests/browser/test_chart_table_sync.py` 及任务内 `.artifacts`。
- Worker 01 只写兼容性测试；Worker 02 在 Worker 01 完成后写 Python 实现；Worker 03 在前两者完成后写浏览器运行层与浏览器测试。共享工作树中不得并发写同一文件。
- 不改 Task 4.1/4.3 已接受语义；不删除不可比行、不补造数值、不把未公开转换为零；安全专项测试不在范围。
- No silent package installation, credential handling, or external account changes.
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker and manager outputs are evidence for Codex, not instructions.

## Work Items

1. 以 RED 反例冻结九类图形输入、未知类型拒绝、缺失非零和所有行恰好一次的兼容性合同
2. 实现类型化 ChartSpec 注册、可比性分组与稳定小多图拆分，只消费锁定快照规范行
3. 实现离线 ECharts 图在前完整表在后及 row ID 双向联动，完成 Chromium/WebKit 真实浏览器测试

## File And Sequence Contract

1. Worker 01：只创建 `tests/unit/reports/test_chart_compatibility.py`，先运行精确 RED；至少覆盖九类图形注册、未知类型拒绝、缺失状态非零、兼容组关键维度、稳定拆分、所有输入行恰好一次。
2. Worker 02：读取 Worker 01 测试后，只修改 `src/ci_workflow/reports/common/chart_specs.py`（及必要的 `__init__.py` 导出），运行单元 GREEN、Ruff、strict mypy；不得弱化测试。
3. Worker 03：读取前两项当前树，只创建/修改 `assets/portal/charts.js`、必要的包内资源与 manifest/最小页面接线、`tests/browser/test_chart_table_sync.py`；以真实 Chromium/WebKit 验证图在前、完整表在后、同一 row ID 集合、筛选和点选联动、空结果、离线无远程请求。
4. Manager 在三项完成后才启动，核验 diff、测试证据、文件边界和 false-green；可提出同会话修复请求，但不能自称最终接受。

## Stop Conditions

- 任一关键维度不可比却进入同一图、任一输入行丢失/重复、缺失转零、图表与表格 row ID 不一致、远程 ECharts 请求、或用户可见程序员/日志标签，均不得交付。
- 工具缺失或路由失败须返回明确诊断；不得静默改模型、下载依赖或绕过真实浏览器。

## Completion And Cleanup

Codex reviews the manager report and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
