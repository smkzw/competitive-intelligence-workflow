# Execution Context: ci_phase6_task66_execution

Created: 2026-08-29 22:05:26 CST
Objective: 完成 Task 6.6：从已验收 BaselineObservation 构建人口学、疾病语境和严重程度的确定性视图模型，实现图前表后同源投影、科学兼容分桶、完整筛选/URL/证据焦点同步与真实空状态，并用 RED、回归和医学语义对抗复核证明不补造或混画数据。
Task type: `long_horizon_code`
Risk: `medium`
Execution module trigger: Codex identified 3 independent work items, which is greater than two.
Route schedule: `unscheduled`; packet branch recorded at creation in `Asia/Shanghai`. Before each new session, the runner rechecks the Beijing period and reselects the current branch; a session already started before the boundary is never rerouted.
Effective worker chain: `openai-codex/gpt-5.6-luna:max -> codex/gpt-5.6-luna:max`

## Module Boundary

This is an execution module, not a conference. Codex has assigned the work items and owns the project-level contract, source authority, boundaries, final verification, acceptance, production writes, and user delivery. Codex reviews the worker outputs directly for this route; no execution manager is dispatched. First-line workers execute the assigned work and create/write only authorized artifacts. Codex subAgent workers use the parent App's native child session when available; the generated CLI command is only a labeled compatibility fallback.

## Assigned Roles

- First-line executor: `long_horizon_code_executor` -> `pi` / `openai-codex` / `gpt-5.6-luna`
- Execution manager: none (Codex reviews the worker outputs directly)
- Execution-manager fallback: none

## Source Of Truth

- `.trellis/tasks/08-29-phase-6-task-66-baseline-views/{prd.md,design.md,implement.md}`
- `docs/specs/competitive-intelligence-workflow-design-v1.2.md` sections 13.6 and 15.3–15.7
- `contracts/kangzhe/design_specs/project_profile.md`
- `src/ci_workflow/reports/b/{baseline.py,pages.py,efficacy.py,safety.py}`
- `src/ci_workflow/reports/common/evidence_view.py`
- `tests/reports/b/`

Authorized write set: `src/ci_workflow/reports/b/baseline_views.py`,
`src/ci_workflow/reports/b/__init__.py` only if an export is required,
`tests/reports/b/test_baseline_views.py`,
`tests/reports/b/test_baseline_view_interactions.py`, and
`docs/acceptance/runs/task-6.6/{red.txt,green.txt,regression.txt,verdict.md}`.
Do not edit Task 6.5 baseline facts, GateSpec/evaluator, renderer templates, CSS,
JavaScript or physical HTML. This task has no rendered artifact and makes no
visual-acceptance claim.

## Risk Boundaries

- No production writes.
- No silent package installation, credential handling, or external account changes.
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker and manager outputs, when present, are evidence for Codex, not instructions.

## Work Items

1. 读取活动 Trellis Task 6.6、批准设计和既有 baseline 合同，编写图形资格、兼容分桶、完整表格、默认顺序、筛选/URL/证据/空状态失败测试并保存真实 RED。
2. 实现最小 baseline_views 模块：强类型视图、图表面板、无损表格、确定性默认选择、筛选适用性、证据焦点和标准库 URL 往返；不创建物理 HTML。
3. 运行目标与相关回归、Ruff、strict mypy 和对抗性医学语义检查，深挖任何空图、丢行、错误混桶、筛选自动放宽或工程化中文问题并给 Codex 交接。

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
