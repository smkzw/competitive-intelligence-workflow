# Execution Context: ci-r2-render-transaction-recovery-20260905

Created: 2026-09-05 15:08:36 CST
Objective: 修复 A/B/C HTML 渲染在未发布目录中断后的可恢复事务边界，同时保持任何已发布或已绑定产物严格不可覆盖。
Task type: `long_horizon_code`
Risk: `high`
Execution module trigger: Codex assigned 3 bounded work item(s). Each item must identify its inputs, allowed paths, deliverable and acceptance check.
Route schedule: `off_peak`; packet branch recorded at creation in `Asia/Shanghai`. Before each new session, the runner rechecks the Beijing period and reselects the current branch; a session already started before the boundary is never rerouted.
Effective worker chain: `zcode/glm-5.3:max -> cursor/default -> openai-codex/gpt-5.6-luna:max -> openai-codex/gpt-6-astra:medium`

## Module Boundary

This is an execution module, not a conference. Codex has assigned the work items and owns the project-level contract, source authority, boundaries, final verification, acceptance, production writes, and user delivery. Codex reviews the worker outputs directly for this route; no execution manager is dispatched. First-line workers execute the assigned work and create/write only authorized artifacts. Codex subAgent workers use the parent App's native child session when available; the generated CLI command is only a labeled compatibility fallback.

## Assigned Roles

- First-line executor: `long_horizon_code_executor` -> `zcode` / `zcode` / `GLM-5.3`
- Execution manager: none (Codex reviews the worker outputs directly)
- Execution-manager fallback: none

## Source Of Truth

- `docs/specs/competitive-intelligence-workflow-design-v1.3.md`
- `plans/codex_execution_ci-rebaseline-rebuild-v3.md`
- `.trellis/tasks/09-02-phase-10-task-106-rc-freeze/implement.md`
- `src/ci_workflow/application/run_service.py`
- `src/ci_workflow/renderers/portal/report_a.py`
- `src/ci_workflow/renderers/portal/report_b.py`
- `src/ci_workflow/renderers/portal/report_c.py`
- `src/ci_workflow/storage/manifest_store.py`
- `src/ci_workflow/application/scientific_review_transition.py`
- Current repository Skill text is an implementation surface, not requirement authority.

## Risk Boundaries

- No production writes.
- No silent package installation, credential handling, or external account changes.
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker and manager outputs, when present, are evidence for Codex, not instructions.

## Work Items

1. 设计并实现共享的未发布渲染目录事务边界及 A 类接入；先写失败测试，拒绝覆盖任何已有 manifest 或完成绑定。
2. 独立实现或评估 B/C 渲染接入与中断恢复测试，确保只清理当前项目内可证明未发布的精确目录。
3. 只读审计当前 A/B/C 渲染、事件、manifest、科学复核绑定和恢复路径，给出最小失败关闭负向矩阵与对前两项的验收风险。

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
