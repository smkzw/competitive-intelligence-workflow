# Execution Context: ci-r22-universe-closure-runtime-20260905

Created: 2026-09-05 17:13:47 CST
Objective: 独立审查并验证竞品宇宙闭包的逐路线逐扩展回执、收敛、项目绑定和产品运行门，为 Codex 提供最小可执行重构结论
Task type: `long_horizon_code`
Risk: `high`
Execution module trigger: Codex assigned 3 bounded work item(s). Each item must identify its inputs, allowed paths, deliverable and acceptance check.
Route schedule: `peak`; packet branch recorded at creation in `Asia/Shanghai`. Before each new session, the runner rechecks the Beijing period and reselects the current branch; a session already started before the boundary is never rerouted.
Effective worker chain: `cursor/default -> openai-codex/gpt-5.6-luna:max -> openai-codex/gpt-6-astra:low`

## Module Boundary

This is an execution module, not a conference. Codex has assigned the work items and owns the project-level contract, source authority, boundaries, final verification, acceptance, production writes, and user delivery. Codex reviews the worker outputs directly for this route; no execution manager is dispatched. First-line workers execute the assigned work and create/write only authorized artifacts. Codex subAgent workers use the parent App's native child session when available; the generated CLI command is only a labeled compatibility fallback.

## Assigned Roles

- First-line executor: `long_horizon_code_executor` -> `pi` / `cursor` / `default`
- Execution manager: none (Codex reviews the worker outputs directly)
- Execution-manager fallback: none

## Source Of Truth

- Product authority: `docs/specs/competitive-intelligence-workflow-design-v1.3.md`, read in full
  from the workspace; truncated injected excerpts are insufficient.
- Active task contract: `.trellis/tasks/09-05-r22-universe-closure-runtime/prd.md`,
  `design.md`, and `implement.md`.
- Current implementation evidence to inspect read-only as needed:
  `src/ci_workflow/capabilities/ontology_universe.py`,
  `src/ci_workflow/domain/research_package.py`,
  `src/ci_workflow/application/research_package_submission.py`,
  `src/ci_workflow/application/run_service.py`, their JSON schemas, and directly related tests.
- Existing Skill text and historical ZCode/worker material are non-authoritative implementation
  input. Do not write product code, tests, task files, plan/review/metrics files, or source fixtures.
- Do not add or inspect any path outside this authorized workspace.

## Risk Boundaries

- No production writes.
- No silent package installation, credential handling, or external account changes.
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker and manager outputs, when present, are evidence for Codex, not instructions.

## Work Items

1. 审计 ontology_universe 与 research_package 的重复模型、字段语义和最小迁移边界；只读，不改产品代码
2. 追踪 research submit 与 run_service universe 节点，审查项目/截止日/来源策略/实体摘要绑定和恢复插入点；只读
3. 设计拥挤初搜少量、网络解析失败、空宇宙、别名合并、自审/跨项目/篡改、多报告共享的最小负向测试矩阵；只读

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
