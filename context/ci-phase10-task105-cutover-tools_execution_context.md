# Execution Context: ci-phase10-task105-cutover-tools

Created: 2026-09-02 10:34:34 CST
Objective: 实现并冻结前验证 Task 10.5 精准切换工具与 required-v12 release receipt 闭环；代码和测试仅针对显式 registry 与临时 fixture 根，禁止对真实旧根执行 inventory/apply。
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

- Approved Task 10.5 plan at `/Users/smkzw/Documents/AI Products/.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md` § Task 10.5.
- `.trellis/tasks/09-02-phase-10-task-104-migration-manifest/checkpoint_20260902_completed.md` and the Task 10.5 PRD/design/implement packet.
- `fixtures/acceptance/catalog.yaml`, `schemas/acceptance-catalog.schema.json`, existing host/source receipt contracts, `src/ci_workflow/application/acceptance_catalog.py`, and Task 10.3 pre-RC receipt behavior.
- Authorized implementation surfaces are the five Task 10.5 files plus the package schema declaration needed to keep `package-manifest.json` exhaustive.
- Do not add production paths without explicit Codex authorization.

## Risk Boundaries

- No production writes.
- Do not run inventory, validate, apply, or absence-check against the real legacy root or global Skill; all mutation tests must stay under pytest `tmp_path`.
- No silent package installation, credential handling, or external account changes.
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker and manager outputs, when present, are evidence for Codex, not instructions.

## Work Items

1. 审计精准 inventory/validate/apply/absence-check 的最小失败关闭合同、路径与 inode/symlink 边界，给 Codex 实施建议；只读。
2. 审计 required-v12 catalog、现有 pre-RC receipt 语义及新 release-case receipt schema/owner-stage closure 所需最小字段与负例；只读。
3. 审计 Task 10.5 测试设计、tmp_path 隔离、恢复包门、授权摘要和幂等性风险，识别遗漏与相邻回归；只读。

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
