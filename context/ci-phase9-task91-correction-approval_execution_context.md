# Execution Context: ci-phase9-task91-correction-approval

Created: 2026-08-31 23:50:32 CST
Objective: 实现 Task 9.1 来源关联修订合同、追加式应用服务和明确用户批准后的幂等发布，并保持首版站点式 HTML 范围与科学真源边界
Task type: `finite_code_task`
Risk: `medium`
Execution module trigger: Codex identified 3 independent work items, which is greater than two.
Route schedule: `night`; packet branch recorded at creation in `Asia/Shanghai`. Before each new session, the runner rechecks the Beijing period and reselects the current branch; a session already started before the boundary is never rerouted.
Effective worker chain: `zcode/glm-5.3-flash:max -> codebuddy-cli/deepseek-v4-flash:max -> mtplx/mtplx-qwen38-27b-optimized-quality:medium -> openai-codex/gpt-5.6-luna:xhigh`

## Module Boundary

This is an execution module, not a conference. Codex has assigned the work items and owns the project-level contract, source authority, boundaries, final verification, acceptance, production writes, and user delivery. Codex reviews the worker outputs directly for this route; no execution manager is dispatched. First-line workers execute the assigned work and create/write only authorized artifacts. Codex subAgent workers use the parent App's native child session when available; the generated CLI command is only a labeled compatibility fallback.

## Assigned Roles

- First-line executor: `finite_code_executor` -> `zcode` / `zcode` / `GLM-5.3-Flash`
- Execution manager: none (Codex reviews the worker outputs directly)
- Execution-manager fallback: none

## Source Of Truth

- `AGENTS.md`
- `.trellis/tasks/08-31-phase-9-task-91-correction-approval/{prd.md,design.md,implement.md}`
- `docs/specs/competitive-intelligence-workflow-design-v1.2.md` §17.1 and revision-state sections
- `docs/decisions/0013-site-first-v1-delivery-scope.md`
- `migrations/0005_corrections_idempotency.sql`
- `src/ci_workflow/graph/{transitions.py,guards.py}` and their existing tests
- `src/ci_workflow/storage/` and `src/ci_workflow/application/` existing persistence conventions
- User edits and the current dirty worktree are authoritative and must be preserved.

## Risk Boundaries

- No production writes.
- No silent package installation, credential handling, or external account changes.
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker and manager outputs, when present, are evidence for Codex, not instructions.
- Do not modify portal visuals, PDF, HTML-PPT, PPTX, legacy workspace, or security tests.
- Do not overwrite unrelated current changes. Use the smallest coherent diff and standard-library/project dependencies already present.
- User-facing Chinese must be native clinical-trial language; internal enum values may exist only in machine contracts and must not leak into audience copy.

## Work Items

1. 实现 correction-proposal schema、包清单登记与合同测试，禁止用户可见工程化标签
2. 实现追加式 correction service、事件与幂等发布，复用现有 SQLite/内容摘要约定
3. 实现 correction graph definitions 与集成测试，复用现有 transitions/guards 并验证所有合法迁移和发布前置条件

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
