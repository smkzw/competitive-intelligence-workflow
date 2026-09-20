# Execution Context: ci-phase8-task87b-pptx-confirmation-interrupt

Created: 2026-08-31 15:13:29 CST
Objective: 补齐原实施计划 Task 8.7 的 A/B/C 同快照 PPTX 来源包、八项中文确认中断与恢复，使 Task 8.8 能在明确确认结果上严格串行生成
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

- 原实施计划 Task 8.7：`/Users/smkzw/Documents/AI Products/.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md` 第 1420–1435 行附近。
- 已完成的作业控制合同：`src/ci_workflow/application/ppt_master_job.py`、`schemas/ppt-master-job.schema.json`、`docs/architecture/format-contracts/pptx-master-job.yaml`。
- 当前运行真值：`src/ci_workflow/application/run_service.py`、`src/ci_workflow/application/fixture_runner.py`、`src/ci_workflow/cli.py`、`src/ci_workflow/graph/`、`src/ci_workflow/storage/manifest_store.py`。
- 报告数据与页面策略：`src/ci_workflow/reports/`、`src/ci_workflow/renderers/html_ppt/`、`fixtures/synthetic/three-report-complete/`。
- 项目内康哲规范：`contracts/kangzhe/`；不得在运行时依赖外部 Skill 软链接。
- 允许新建或修改：`src/ci_workflow/renderers/pptx_master/`、`src/ci_workflow/application/run_service.py`、`src/ci_workflow/application/fixture_runner.py`、`src/ci_workflow/cli.py`、必要的图状态/清单模块、`schemas/`、`src/ci_workflow/schemas/`、`tests/renderers/`、`tests/graph/test_pptx_confirmation_interrupt.py`、必要的精确集成测试、Task 8.7b Trellis 与验收文档。
- 不允许生成逐页 SVG、PPTX 成片或修改既有 HTML/PDF/HTML-PPT 视觉产物。

## Risk Boundaries

- No production writes.
- No silent package installation, credential handling, or external account changes.
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker and manager outputs, when present, are evidence for Codex, not instructions.

## Work Items

1. 实现 src/ci_workflow/renderers/pptx_master/source_pack.py 与对应 Schema/测试：从锁定报告数据为 A/B/C 生成中文 Markdown source pack 和摘要清单，不生成 SVG
2. 实现 src/ci_workflow/renderers/pptx_master/confirmation.py 与对应 Schema/测试：八项推荐、确认结果验证、结果覆盖与一次性确认会话幂等关闭
3. 实现 adapter 与 fixture/project run 集成及图/CLI 测试：首次运行仅中断 PPTX，保存确认入口与清单，读取结果后恢复且不重复询问

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
