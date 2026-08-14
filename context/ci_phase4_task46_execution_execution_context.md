# Execution Context: ci_phase4_task46_execution

Created: 2026-08-14 12:30:47
Objective: 实现 Task 4.6 全站浏览器验收工具及其确定性测试
Task type: `finite_code_task`
Risk: `high`
Execution module trigger: Codex identified 3 independent work items, which is greater than two.

## Module Boundary

This is an execution module, not a conference. Codex has assigned the work items and owns the project-level contract, source authority, boundaries, final verification, acceptance, production writes, and user delivery. Codex reviews the worker outputs directly for this route; no execution manager is dispatched. First-line workers execute the assigned work and create/write only authorized artifacts. Codex subAgent workers use the parent App's native child session when available; the generated CLI command is only a labeled compatibility fallback.

## Assigned Roles

- First-line executor: `finite_code_executor_cms` -> `pi` / `cms-smk` / `deepseek-v4-flash`
- Execution manager: none (Codex reviews the worker outputs directly)
- Execution-manager fallback: none

## Source Of Truth

- `context/ci_phase4_task46_context.md`。
- `docs/specs/competitive-intelligence-workflow-design-v1.2.md` §15.1–15.6。
- `../.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md` Task 4.6（只读）。
- `.trellis/tasks/08-13-phase-4-common-report-portal/{prd.md,task.json}`。
- `src/ci_workflow/reports/common/{page_registry,view_state}.py`、`src/ci_workflow/renderers/portal/`、`tests/browser/` 的当前已接受合同。

## Risk Boundaries

- No production writes.
- No silent package installation, credential handling, or external account changes.
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker and manager outputs, when present, are evidence for Codex, not instructions.
- 不做安全测试，不访问外网；验收器不得自动修改被验收站点。
- 用户可见 CLI 结果使用自然中文，不显示后端枚举、门、信号或提示词。

## Work Items

1. 先写站点地图集合一一对应失败测试，再实现静态责任页与每个产品/试验动态详情页枚举合同
2. 先写死链、控制台、远程请求、重复 footer、溢出与遮挡失败测试，再实现只读验收器核心
3. 先写 Chromium/WebKit 1280/1440/1920 运行时失败测试，再实现 CLI、原分辨率截图和交互 trace 输出

## Authorized Outputs And Order

- worker_01 first：`src/ci_workflow/qc/browser.py`、必要的 `src/ci_workflow/qc/__init__.py`、`tests/acceptance/test_portal_runtime.py` 中 sitemap 节点。先完成并终止后才启动 worker_02。
- worker_02 second：在 worker_01 当前树上只扩展 `src/ci_workflow/qc/browser.py` 与 `tests/acceptance/test_portal_runtime.py` 的只读缺陷检测节点；不得重写 sitemap 合同。
- worker_03 third：在前两项当前树上实现 `tools/verify_portal.py`、必要的测试夹具和 `tests/acceptance/test_portal_runtime.py` 的 CLI/双浏览器/多视口/截图/trace 节点。
- 每位 worker 必须先记录 RED，再实现 GREEN；只运行与当前工作项有关的测试及必要邻接回归。

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
