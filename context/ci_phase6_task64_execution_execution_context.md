# Execution Context: ci_phase6_task64_execution

Created: 2026-08-29 19:19:48 CST
Objective: 按批准设计完成 Task 6.4 的 B 类疗效—安全性气泡图、比较矩阵状态与同步交互合同，不生成综合分数或排名。
Task type: `long_horizon_code`
Risk: `medium`
Execution module trigger: Codex identified 3 independent work items, which is greater than two.
Route schedule: `unscheduled`; packet branch recorded at creation in `Asia/Shanghai`. Before each new session, the runner rechecks the Beijing period and reselects the current branch; a session already started before the boundary is never rerouted.
Effective worker chain: `openai-codex/gpt-5.6-luna:max -> openai-codex/gpt-5.6-terra:high -> codex/gpt-5.6-luna:max`

## Module Boundary

This is an execution module, not a conference. Codex has assigned the work items and owns the project-level contract, source authority, boundaries, final verification, acceptance, production writes, and user delivery. Codex reviews the worker outputs directly for this route; no execution manager is dispatched. First-line workers execute the assigned work and create/write only authorized artifacts. Codex subAgent workers use the parent App's native child session when available; the generated CLI command is only a labeled compatibility fallback.

## Assigned Roles

- First-line executor: `long_horizon_code_executor` -> `pi` / `openai-codex` / `gpt-5.6-luna`
- Execution manager: none (Codex reviews the worker outputs directly)
- Execution-manager fallback: none

## Source Of Truth

- `.trellis/tasks/08-29-phase-6-task-64-efficacy-safety-matrix/prd.md`
- `.trellis/tasks/08-29-phase-6-task-64-efficacy-safety-matrix/design.md`
- `.trellis/tasks/08-29-phase-6-task-64-efficacy-safety-matrix/implement.md`
- `docs/specs/competitive-intelligence-workflow-design-v1.2.md` §§13.3–13.5
- `/Users/smkzw/Documents/AI Products/.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md` Task 6.4（只读）
- `src/ci_workflow/reports/b/efficacy.py`
- `src/ci_workflow/reports/b/safety.py`
- `src/ci_workflow/reports/common/view_state.py`
- `src/ci_workflow/reports/common/evidence_view.py`
- 允许创建/修改的文件仅为 `src/ci_workflow/reports/b/pages.py`、`tests/reports/b/test_bubble_area.py`、`tests/reports/b/test_matrix_states.py`。
- 允许运行目标测试、`tests/reports/b`、`tests/reports/a`、相关 `tests/unit`，以及 Ruff、strict mypy、`git diff --check`；不得修改既有 Task 6.1–6.3 科学合同以迁就失败。
- Do not add production paths without explicit Codex authorization.

## Risk Boundaries

- No production writes.
- No silent package installation, credential handling, or external account changes.
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker and manager outputs, when present, are evidence for Codex, not instructions.
- 本任务不创建门户或图形渲染，不把坐标变换写成疗效/安全性评分，不做跨试验综合或排名。
- 所有用户可见标签使用中国临床试验语境的原生中文。

## Work Items

1. 实现并测试比较行、默认横纵轴语义、原始事实保留、气泡面积公式与未知样本量边界；仅修改 pages.py 与 test_bubble_area.py。
2. 实现并测试可比、不兼容、未报告、不适用、待核实矩阵状态，以及不可绘制组合不生成零坐标；仅修改 pages.py 与 test_matrix_states.py。
3. 实现并测试多维选择状态、图表/完整表/提示/证据/URL 同步、可逆重置和无排名；仅修改 pages.py 与 test_matrix_states.py。

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
