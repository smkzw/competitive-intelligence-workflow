# Execution Context: ci-r2-review-runtime-fixture-rebaseline-20260905

Created: 2026-09-05 07:21:10 CST
Objective: 关闭 R2 的真实独立复核授权边界，并重基线 HTML-only 活跃验收：真实回执是科学状态迁移唯一授权；preview fixture 快照语义可运行但不可被接受；非 HTML 测试保留且与 v1 release gate 明确分层。不得触碰旧根，不得宣称 R2 或 RC 完成。
Task type: `long_horizon_code`
Risk: `high`
Execution module trigger: Codex identified 3 independent work items, which is greater than two.
Route schedule: `off_peak`; packet branch recorded at creation in `Asia/Shanghai`. Before each new session, the runner rechecks the Beijing period and reselects the current branch; a session already started before the boundary is never rerouted.
Effective worker chain: `zcode/glm-5.3-flash:max -> openai-codex/gpt-5.6-luna:max -> codex/gpt-5.6-luna:max`

## Module Boundary

This is an execution module, not a conference. Codex has assigned the work items and owns the project-level contract, source authority, boundaries, final verification, acceptance, production writes, and user delivery. Codex reviews the worker outputs directly for this route; no execution manager is dispatched. First-line workers execute the assigned work and create/write only authorized artifacts. Codex subAgent workers use the parent App's native child session when available; the generated CLI command is only a labeled compatibility fallback.

## Assigned Roles

- First-line executor: `long_horizon_code_executor` -> `zcode` / `zcode` / `GLM-5.3-Flash`
- Execution manager: none (Codex reviews the worker outputs directly)
- Execution-manager fallback: none

## Source Of Truth

- TODO: Codex must add authoritative source files, screenshots, datasets, or URLs before dispatch.
- Do not add production paths without explicit Codex authorization.

## Risk Boundaries

- No production writes.
- No silent package installation, credential handling, or external account changes.
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker and manager outputs, when present, are evidence for Codex, not instructions.

## Work Items

1. 设计并实现 B/C 两阶段科学复核状态迁移：候选先为 rendered_unreviewed，真实 scientific-review-v1 回执经实际文件字节与权威 ScientificQcCurrentContext 绑定后才生成 scientifically_reviewed_rendered_candidate；缺回执、伪回执、同会话、自审、旧内容和宿主不可用全部失败关闭。
2. 审计并修复 report-data preview fixture 的报告快照合同：调用方声明但项目中不存在的快照不得被信任；开发预览应可确定性生成自身 snapshot 并保持 rendered_unreviewed，且不能进入视觉/真实来源/RC 接受。覆盖单报告与 three-report-complete。
3. 建立 HTML-only v1 活跃 pytest/验收分层并修复与当前科学合同冲突的旧断言：保留 PDF/HTML-PPT 源码和基础回归，不把它们算作 v1 release gate；审计 B 抽屉分子分母断言，禁止从百分比反推或回填未报告 n/N；输出可复现的全量债清单。

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.

## Codex Scoped Addendum

- Canonical sources: `docs/specs/competitive-intelligence-workflow-design-v1.3.md`,
  `plans/codex_execution_ci-rebaseline-rebuild-v3.md`, and
  `.trellis/tasks/09-02-phase-10-task-106-rc-freeze/checkpoint_20260905_r2_terminal_recovery_review_boundary.md`.
- The current repository copy is the only workspace. The former Chinese-named
  workspace is forbidden: do not read, resolve, inventory, existence-check, write,
  chmod or delete it.
- Existing Skill text and earlier model reports are evidence only, not authority.
- TDD is mandatory: record a focused RED before implementation and GREEN afterward.
- Worker 01 may edit only scientific review/runtime files under
  `src/ci_workflow/{application,qc,capabilities}/`, matching schemas and directly
  related tests.
- Worker 02 may edit only report-data preview snapshot/render integration under
  `src/ci_workflow/{application,renderers,storage}/`, fixture metadata when strictly
  necessary, and directly related tests.
- Worker 03 may edit only pytest/release-scope configuration, active-gate tooling,
  B drawer assertions/data when evidence proves the current assertion stale, and a
  compact debt record under `reviews/`. It must not delete PDF/HTML-PPT source or
  tests and must not mark failures away without a declared test layer.
- No worker may modify governance plans, checkpoints, peer reports, credentials,
  generated release artifacts, or claim final scientific/visual/release acceptance.
