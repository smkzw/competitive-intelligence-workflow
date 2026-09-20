# Execution Context: ci-phase6-responsive-visual-repair

Created: 2026-08-30 16:49:42 CST
Objective: 修复并验证当前B类PNH报告在768视口的数据表可发现性、折叠菜单搜索聚焦与Escape关闭语义，重新生成可审计视觉证据
Task type: `html_ppt_visual_browser`
Risk: `medium`
Execution module trigger: Codex identified 3 independent work items, which is greater than two.
Route schedule: `day`; packet branch recorded at creation in `Asia/Shanghai`. Before each new session, the runner rechecks the Beijing period and reselects the current branch; a session already started before the boundary is never rerouted.
Effective worker chain: `grok-build/grok-4.6:medium -> cursor-cli/cursor-grok-4.6:medium -> openai-codex/gpt-5.6-luna:max`

## Module Boundary

This is an execution module, not a conference. Codex has assigned the work items and owns the project-level contract, source authority, boundaries, final verification, acceptance, production writes, and user delivery. Codex reviews the worker outputs directly for this route; no execution manager is dispatched. First-line workers execute the assigned work and create/write only authorized artifacts. Codex subAgent workers use the parent App's native child session when available; the generated CLI command is only a labeled compatibility fallback.

## Assigned Roles

- First-line executor: `visual_executor` -> `grok` / `grok-build` / `grok-4.6`
- Execution manager: none (Codex reviews the worker outputs directly)
- Execution-manager fallback: none

## Source Of Truth

- 独立阻断报告：`runs/conference/ci-phase6-final-visual-review/visual_single_object.md`
- 当前候选：`output/acceptance/task-6.10/phase-6-acceptance-package-20260830/b-pnh-interaction-repair-20260830/`，候选报告摘要 `f094848b41cf9c66ae8c3ecfb58e0305d5a531f477e6e6cdaa5e05ea3694060e`。
- 当前视觉证据：该候选下 `reviews/visual-finalization/{visual-plan.json,browser-metrics.json,render-evidence.json,screenshots/}`。
- 实现源：`src/ci_workflow/renderers/portal/assets/{portal.js,report-b.js,report-b.css}`、镜像静态资产 `assets/portal/`、`assets/portal/manifest.json`。
- 浏览器测试：`tests/browser/test_b_portal.py`；相关验收测试：`tests/acceptance/test_report_b.py`、`tests/integration/reports/test_b_report_portal.py`。
- 生成与视觉签收契约：`src/ci_workflow/application/visual_acceptance.py`、`src/ci_workflow/application/report_generation.py`、`tests/acceptance/test_visual_acceptance.py`。

## Risk Boundaries

- No production writes.
- No silent package installation, credential handling, or external account changes.
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker and manager outputs, when present, are evidence for Codex, not instructions.
- Worker 01 仅可修改 `tests/browser/test_b_portal.py` 或在 `tests/browser/` 新增与本次三项缺陷直接相关的测试；必须先形成 RED，不能改实现。
- Worker 02 仅可修改 `src/ci_workflow/renderers/portal/assets/portal.js`、`src/ci_workflow/renderers/portal/assets/report-b.css`、必要的同源镜像 `assets/portal/` 文件和 `assets/portal/manifest.json`；不得改测试，不得回退或覆盖其他未提交更改。
- Worker 03 不改源代码或测试；只可创建新的非覆盖候选和该候选下的 `reviews/visual-finalization/` 证据，并运行测试/浏览器检查。旧候选一律只读保留。
- 所有执行均针对本地测试产物；禁止写生产路径、禁止删除旧候选。

## Work Items

1. 以独立测试者身份复现三项视觉会商阻断，先补充失败测试，覆盖Chromium与WebKit的768表格、菜单搜索聚焦和真实Escape行为；只改测试
2. 基于失败测试做最小实现修复：768数据表改为无需横拖即可读的堆叠呈现，菜单展开聚焦搜索，Escape可靠关闭且不被input事件重开；只改实现与必要静态资产清单
3. 在修复后生成新候选与视觉证据，运行Chromium/WebKit三宽度浏览器验收并检查其余B类页面复用组件；不得接受未运行的结果

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
