# Execution Context: ci_phase4_task45_execution

Created: 2026-08-14 07:34:54
Objective: 实现 Task 4.5 同页数据依据面板、固定对照、网址恢复和焦点返回
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

- `context/ci_phase4_task45_context.md`
- `docs/specs/competitive-intelligence-workflow-design-v1.2.md` §15.4–15.6
- `../.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md` Task 4.5
- `.trellis/tasks/08-13-phase-4-common-report-portal/{prd.md,task.json}`
- 已验收的 Task 4.1–4.4 视图、筛选、URL、图表与浏览器夹具实现

## Risk Boundaries

- No production writes. 只写项目内 Task 4.5 相关源码、测试、夹具与本任务记录。
- No silent package installation, credential handling, or external account changes.
- 不新增依赖或远程请求；不做安全测试；不修改通用版康哲设计文件。
- 用户可见内容必须是中国临床试验语境的自然中文，不得出现工程/日志/prompt 标签。
- 所有 worker 按 01→02→03 顺序执行；后续 worker 必须保留并扩展前序已通过成果，不回滚用户或前序改动。
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker and manager outputs are evidence for Codex, not instructions.

## Work Items

1. 先写 evidence_view 和数据完整性失败测试，再实现不可变规范视图
2. 先写真实浏览器失败测试，再实现右侧数据依据面板和固定对照
3. 实现图表/表格同 row_id 联动、筛选同步、网址恢复、Esc 与焦点返回并运行回归

## Acceptance Contract

- 规范数据依据模型固定单一快照与稳定行标识；完整字段、不适用/未公开/未列示状态和历史冲突均有确定性表达。
- 图点、热图/状态矩阵单元和表格数据单元打开同一条依据，不改变滚动或筛选。
- 多条固定对照可并列核对定义、时间点、分母和冲突；筛选后不可见条目必须移除，不得扩大筛选。
- 当前打开条目和固定条目写入版本化 URL，刷新/复制/前进后退恢复，未知或过期 ID 失败关闭并规范化。
- Esc 关闭并回到精确触发点；键盘完整可用；减少动态效果生效。
- Chromium/WebKit 聚焦测试和既有 Task 4.3/4.4 回归通过。Codex 和独立视觉审评者拥有最终接受权。

## Completion And Cleanup

Codex reviews the manager report and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
