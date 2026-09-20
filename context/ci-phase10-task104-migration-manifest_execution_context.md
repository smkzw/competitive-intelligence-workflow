# Execution Context: ci-phase10-task104-migration-manifest

Created: 2026-09-02 09:50:14 CST
Objective: 完成 Task 10.4 批准迁移清单闭环：精确保留白名单、显式排除旧实现与敏感运行状态、提供 schema/测试/中文验收证据，但不执行真实旧根切换或删除。
Task type: `finite_code_task`
Risk: `medium`
Execution module trigger: Codex identified 3 independent work items, which is greater than two.
Route schedule: `off_peak`; packet branch recorded at creation in `Asia/Shanghai`. Before each new session, the runner rechecks the Beijing period and reselects the current branch; a session already started before the boundary is never rerouted.
Effective worker chain: `zcode/glm-5.3-flash:max -> codebuddy-cli/deepseek-v4-flash:max -> mtplx/qwen3.8-flash-next-mtplx-optimized-speed:medium -> openai-codex/gpt-5.6-luna:xhigh`

## Module Boundary

This is an execution module, not a conference. Codex has assigned the work items and owns the project-level contract, source authority, boundaries, final verification, acceptance, production writes, and user delivery. Codex reviews the worker outputs directly for this route; no execution manager is dispatched. First-line workers execute the assigned work and create/write only authorized artifacts. Codex subAgent workers use the parent App's native child session when available; the generated CLI command is only a labeled compatibility fallback.

## Assigned Roles

- First-line executor: `finite_code_executor` -> `zcode` / `zcode` / `GLM-5.3-Flash`
- Execution manager: none (Codex reviews the worker outputs directly)
- Execution-manager fallback: none

## Source Of Truth

- 批准实施计划 Task 10.4：`/Users/smkzw/Documents/AI Products/.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md`。
- 批准规格：`docs/specs/competitive-intelligence-workflow-design-v1.2.md` §20.3–20.4。
- 旧迁移登记与 schema：`migration/legacy_manifest.jsonl`、`migration/legacy_manifest.schema.json`。
- 项目内化设计来源链：`docs/decisions/0002-kangzhe-contract-reconciliation.md`、`docs/decisions/0005-kangzhe-design-spec-repair-contract.md`、`contracts/kangzhe/manifest.json`。
- Task 10.3 完成检查点：`.trellis/tasks/09-01-phase-10-task-103-html-host-full-matrix/checkpoint_20260902_r13k_completed.md`。
- 旧根只读来源：`/Users/smkzw/Documents/AI Products/竞品调研工作流`；不得写入、切换或删除。

## Risk Boundaries

- No production writes.
- No silent package installation, credential handling, or external account changes.
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker and manager outputs, when present, are evidence for Codex, not instructions.

## Work Items

1. 只读核对批准规格、D01-D70、项目内化设计合同、Logo、授权 fixture 与回归断言的来源链、摘要和最终目标，输出白名单建议与缺口。
2. 审查并提出 legacy manifest schema 与闭环测试的不变量、负例和失败关闭要求，不修改任务范围。
3. 只读核对旧代码/schema/模板/QC、全局事实库、会话/缓存/明文凭据、绝对路径和兼容包装器的排除覆盖，并审阅中文迁移说明应披露的边界。

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
