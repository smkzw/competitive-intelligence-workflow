# Execution Context: ci-phase6-closeout-integrity

Created: 2026-08-30 12:55:26 CST
Objective: 修复第6阶段B类报告的视觉验收状态链与持久化验收包，完成包级退出验证后再允许进入第7阶段
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

- `src/ci_workflow/application/run_service.py`
- `src/ci_workflow/renderers/portal/report_b.py`
- `src/ci_workflow/storage/manifest_store.py`
- `src/ci_workflow/graph/visual_finalization.py`
- `src/ci_workflow/graph/guards.py`
- `src/ci_workflow/graph/recovery.py`
- `tests/acceptance/test_report_b.py`
- `tests/contract/test_visual_render_evidence.py`
- `tests/graph/test_visual_finalization_graph_negative.py`
- `fixtures/positive/b-pnh/` and `fixtures/synthetic/b-d70-*/`
- `output/acceptance/task-6.10/b-pnh-current-v9/`
- `docs/acceptance/report-b.md` and `docs/acceptance/runs/task-6.10/checkpoint.md`
- `.trellis/tasks/08-27-phase-6-report-b/` and `.trellis/tasks/08-30-phase-6-task-610-b-d70-acceptance/`
- Do not add production paths without explicit Codex authorization.

## Risk Boundaries

- No production writes.
- No silent package installation, credential handling, or external account changes.
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker and manager outputs, when present, are evidence for Codex, not instructions.
- This repository contains extensive in-progress user/Codex changes. Preserve them. Do not reset, overwrite, clean broadly, or edit the legacy sibling workspace.
- Worker 01 may add focused RED tests and a compact audit note only.
- Worker 02 may edit the minimal application/manifest/CLI code and focused tests needed for the visual-acceptance state chain.
- Worker 03 may create durable acceptance artifacts and update only Phase-6 acceptance/Trellis records after deterministic checks pass; it must not claim final visual acceptance.
- Do not delete any old candidate or evidence during this pass. Codex owns final cleanup.

## Work Items

1. 审计并以测试锁定生成态、视觉验收态与可交付态的唯一合法状态链
2. 实现最小视觉验收持久化入口与清单继承关系，修复B类报告提前可交付问题
3. 生成并核验PNH及三个D70场景的持久化验收包，完成第6阶段退出证据与Trellis记录

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
