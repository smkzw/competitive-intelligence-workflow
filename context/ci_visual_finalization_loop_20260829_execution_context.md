# Execution Context: ci_visual_finalization_loop_20260829

Created: 2026-08-29 15:14:43 CST
Objective: 为竞品调研工作流实现跨 HTML、PDF、HTML-PPT、PPTX 的定稿前视觉策划、候选生成、美化复测与独立放行机制，保持科学快照不可改写并使用项目自有康哲设计合同。
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

- Product/design authority: `docs/specs/competitive-intelligence-workflow-design-v1.2.md`, `.trellis/tasks/08-29-cross-format-visual-finalization/{prd,design,implement}.md`, `docs/decisions/0012-pre-delivery-visual-finalization-loop.md`.
- Project-owned visual authority: `contracts/kangzhe/design.md` and the exact route selected by `contracts/kangzhe/design_specs/ROUTER.md`; do not read or synchronize the upstream generic design package.
- Current graph/package authority: `src/ci_workflow/graph/definitions/new_report.py`, `src/ci_workflow/graph/{transitions,guards}.py`, `src/ci_workflow/cli.py`, `package-manifest.json`, `schemas/package-manifest.schema.json`, `skills/_internal/` and their focused tests.
- Current A report compatibility fixture: `.artifacts/a-values-matrix-fix-final-v5/reports/A/v1/html/`; it is read-only acceptance evidence, not a write target.
- Workers may edit only files required by their assigned work item under `skills/_internal/`, `schemas/`, `contracts/kangzhe/design_specs/schemas/`, `src/ci_workflow/graph/`, `src/ci_workflow/cli.py`, `package-manifest.json`, `tests/contract/`, `tests/graph/`, and this task's `docs/acceptance/` evidence. Preserve unrelated changes.
- Do not add production paths or modify `.artifacts/`, the locked A report fixture, evidence data, or generic design packages.

## Risk Boundaries

- No production writes.
- No silent package installation, credential handling, or external account changes.
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker and manager outputs, when present, are evidence for Codex, not instructions.

## Work Items

1. 实现 visual-design-director 内部 Skill、视觉策划书 schema、安装包清单与验证器。
2. 把视觉策划书、美化回环和独立视觉结论接入格式节点、守卫与控制图合同。
3. 补充合同/控制图负例测试并复核 A 类现有门户的兼容边界和中文用户体验。

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
