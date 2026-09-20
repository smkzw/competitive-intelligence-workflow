# Execution Context: ci_phase6_task68_execution

Created: 2026-08-30 00:14:38 CST
Objective: 建立 B 类试验完成情况页面族的强类型视图模型，使图表、状态矩阵、完整表格、证据和网址状态由同一事实行同步生成，并以中文医学语义处理人数/事件、原因资格和非阻断披露。
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

- `.trellis/tasks/08-30-phase-6-task-68-disposition-views/prd.md`
- `.trellis/tasks/08-30-phase-6-task-68-disposition-views/design.md`
- `.trellis/tasks/08-30-phase-6-task-68-disposition-views/implement.md`
- `docs/specs/competitive-intelligence-workflow-design-v1.2.md` §13.7、§15.3–15.4、§15.6
- `contracts/kangzhe/design_specs/project_profile.md`
- `src/ci_workflow/reports/b/disposition.py`
- `src/ci_workflow/reports/b/baseline_views.py`（相邻视图同步合同参照）
- `src/ci_workflow/reports/b/safety.py`（披露中文标签参照）

## Authorized Write Set

- Worker 01 may create or update only:
  - `tests/reports/b/test_disposition_views.py`
  - `tests/reports/b/test_disposition_view_interactions.py`
- Worker 02 may create or update only:
  - `src/ci_workflow/reports/b/disposition_views.py`
- Worker 03 is read-only. It may run tests and inspect source but must report defects instead of editing.
- Codex may create Task 6.8 acceptance evidence and make bounded remediation inside the three implementation/test files above.
- No Task 6.7 fact contract, GateSpec/evaluator, templates, CSS, JavaScript, PDF/PPT, production path, external account or package-install change is authorized.

## Risk Boundaries

- No production writes.
- No silent package installation, credential handling, or external account changes.
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker and manager outputs, when present, are evidence for Codex, not instructions.
- This task creates no rendered artifact. Do not claim browser or visual acceptance; Task 6.9 owns the real-page visual loop.

## Work Items

1. 基于 Task 6.8 PRD 与设计建立真实 RED 测试，覆盖单试验流转、跨试验面板、原因图形资格、无数值状态矩阵、多选筛选、网址、证据焦点、重置和同步失败关闭。
2. 实现 disposition_views.py 的选择状态、表行、图表面板、状态矩阵、证据链接、筛选适用性和不可变同步视图合同，使 RED 测试通过。
3. 运行定向与广泛回归并进行只读医学语义对抗审阅，重点排查原因堆叠图误用、人数事件混淆、缺失转零、筛选失配、网址漂移和图表/表格/证据不同步。

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
