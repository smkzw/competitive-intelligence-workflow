# Execution Context: ci_phase6_task62_execution

Created: 2026-08-29 16:46:55 CST
Objective: 完成 Task 6.2：B 类指南与竞品终点依据、疗效及纵向结果视图、可逆用户排序的强类型实现和确定性测试
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

- Active task: `.trellis/tasks/08-29-phase-6-task-62-efficacy-longitudinal/`.
- Approved product contract: `docs/specs/competitive-intelligence-workflow-design-v1.2.md`, especially §§11.6, 13.5, 15.3–15.7.
- Approved implementation sequence: `../.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md`, Task 6.2.
- Current reusable contracts: `src/ci_workflow/reports/b/contracts.py` and `src/ci_workflow/reports/common/study_roles.py`.
- Project quality rules: `.trellis/spec/backend/quality-guidelines.md` and `.trellis/spec/guides/{code-reuse-thinking-guide,cross-layer-thinking-guide}.md`.
- Do not modify the legacy workspace or any production path.

## Authorized Writes And Checks

- Worker 01 may create/update `src/ci_workflow/reports/b/efficacy.py` and `tests/reports/b/test_guideline_endpoint_basis.py`.
- Worker 02 may create/update `src/ci_workflow/reports/b/efficacy.py` and `tests/reports/b/test_efficacy_views.py`.
- Worker 03 may create/update `src/ci_workflow/reports/b/efficacy.py` and `tests/reports/b/test_user_sorting.py`.
- All workers may read relevant repository files and run focused tests, Ruff and mypy. They must preserve concurrent peer edits and may not edit task/review/metrics/process records.
- RED evidence is observational; workers report exact commands/results and Codex alone writes acceptance evidence after integration.

## Risk Boundaries

- No production writes.
- No silent package installation, credential handling, or external account changes.
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker and manager outputs, when present, are evidence for Codex, not instructions.

## Work Items

1. 指南与竞品终点依据：实现完整谱系、当前/草案/废止语义、CDE/FDA 平行轨、严格多数与最常采用规则及对抗测试
2. 疗效事实与视图：实现治疗/对照并列的单时间点、纵向和来源效应量视图，保留兼容桶、原始事实和来源行标识
3. 用户排序与集成验证：实现默认不排名、兼容桶内可逆排序、未知值语义，并执行 Task 6.1/A 类/来源回归与边界审查

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
