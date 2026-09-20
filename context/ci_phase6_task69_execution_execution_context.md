# Execution Context: ci_phase6_task69_execution

Created: 2026-08-30 01:44:17 CST
Objective: 构建 B 类完整多页面门户、动态产品/试验档案及同源筛选、网址和数据依据交互，并为真实浏览器视觉验收生成可运行站点
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

- `.trellis/tasks/08-30-phase-6-task-69-report-b-portal/prd.md`
- `.trellis/tasks/08-30-phase-6-task-69-report-b-portal/design.md`
- `.trellis/tasks/08-30-phase-6-task-69-report-b-portal/implement.md`
- `.trellis/tasks/08-27-phase-6-report-b/prd.md`
- `docs/specs/competitive-intelligence-workflow-design-v1.2.md` §13.7、§15.3–15.5、§16
- `src/ci_workflow/reports/common/page-catalogs/B.yaml`
- `contracts/kangzhe/design_specs/core.md`
- `contracts/kangzhe/design_specs/track_interactive.md`
- `contracts/kangzhe/design_specs/project_profile.md`
- `docs/decisions/0012-pre-delivery-visual-finalization-loop.md`
- 已验收的 `src/ci_workflow/reports/b/` 视图合同与现有门户壳、筛选、图表、网址和数据依据模块。
- 外部调研仅转译为设计原则：McKinsey 公开年度图表的结论先行/直接标注；W3C WAI 的语义表格和复杂图形替代内容；MDN 的渐进式页面过渡。不得引入远程运行依赖。
- Do not add production paths without explicit Codex authorization.

## Risk Boundaries

- No production writes.
- 只生成本地测试/验收站点，不发布、不覆盖已交付报告。
- 不修改 Task 6.1–6.8 医学事实、证据门槛或视图语义；模板和 JS 不重新推断医学含义。
- 不生成 PDF/PPT，不执行系统安全测试。
- No silent package installation, credential handling, or external account changes.
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker and manager outputs, when present, are evidence for Codex, not instructions.

## Work Items

1. 建立 B 门户静态路由、动态档案、同源图表表格证据与清单的真实 RED 测试
2. 实现 B 门户数据合同、物理页面、离线图表、筛选网址和数据依据交互
3. 运行目标与广泛回归并以真实医学经理视角只读审阅功能完整性、中文原生性和可视化缺陷

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
