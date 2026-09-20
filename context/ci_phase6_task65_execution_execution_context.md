# Execution Context: ci_phase6_task65_execution

Created: 2026-08-29 21:10:05 CST
Objective: 完成 Task 6.5：建立 B 类基线观察事实合同、科学兼容键、JSON Schema 与现有逐试验逐组 GateSpec 的严格绑定，并以真实 RED/GREEN、回归和独立医学语义复核证明不会跨组借值或放宽草稿阻断。
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

- `.trellis/tasks/08-29-phase-6-task-65-baseline-observation/{prd.md,design.md,implement.md}`
- `docs/specs/competitive-intelligence-workflow-design-v1.2.md` section 13.6
- `policies/gates/B-v1.yaml`
- `src/ci_workflow/gates/{models.py,evaluator.py}`
- `src/ci_workflow/domain/{enums.py,evidence.py,ids.py}`
- `src/ci_workflow/reports/b/{contracts.py,efficacy.py,safety.py}`
- `tests/reports/test_report_specific_gates.py`
- `.trellis/spec/backend/quality-guidelines.md`

Authorized write set: `src/ci_workflow/reports/b/baseline.py`,
`src/ci_workflow/reports/b/__init__.py` only if an export is required,
`schemas/baseline-observation.schema.json`,
`tests/reports/b/test_baseline_observation_contract.py`,
`tests/reports/b/test_baseline_group_gate.py`, and
`docs/acceptance/runs/task-6.5/{red.txt,green.txt,regression.txt,verdict.md}`.
Do not edit existing GateSpec policy or evaluator semantics. This task has no
HTML/PDF/PPT output and makes no visual-acceptance claim.

## Risk Boundaries

- No production writes.
- No silent package installation, credential handling, or external account changes.
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker and manager outputs, when present, are evidence for Codex, not instructions.

## Work Items

1. 先读取活动 Trellis 任务、批准设计、B-v1 GateSpec 和既有 gate API，编写并运行失败测试，保存真实 RED 证据。
2. 实现最小 BaselineObservation 合同、科学兼容键、稳定身份、JSON Schema 及到既有 GateEvidenceBinding 的严格转换，不新增门槛引擎。
3. 运行定向与相关回归、静态检查和对抗性用例，核对来源未公开与技术路径未解决的区分，输出紧凑交接供 Codex 验收。

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
