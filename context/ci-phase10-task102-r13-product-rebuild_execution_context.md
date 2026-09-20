# Execution Context: ci-phase10-task102-r13-product-rebuild

Created: 2026-09-01 21:53:31 CST
Objective: 重构站点式 HTML 的 A 图表下钻与空 AESI 隐藏、B 临床语义模糊匹配与真正跨试验横向图表、C 全字段研究设计矩阵，并补齐真实医学经理任务导向的浏览器验收；仅 HTML，不做 PDF/PPT，不做安全专项测试。
Task type: `long_horizon_code`
Risk: `medium`
Execution module trigger: Codex identified 4 independent work items, which is greater than two.
Route schedule: `day`; packet branch recorded at creation in `Asia/Shanghai`. Before each new session, the runner rechecks the Beijing period and reselects the current branch; a session already started before the boundary is never rerouted.
Effective worker chain: `openai-codex/gpt-5.6-luna:max -> codex/gpt-5.6-luna:max`

## Module Boundary

This is an execution module, not a conference. Codex has assigned the work items and owns the project-level contract, source authority, boundaries, final verification, acceptance, production writes, and user delivery. Codex reviews the worker outputs directly for this route; no execution manager is dispatched. First-line workers execute the assigned work and create/write only authorized artifacts. Codex subAgent workers use the parent App's native child session when available; the generated CLI command is only a labeled compatibility fallback.

## Assigned Roles

- First-line executor: `long_horizon_code_executor` -> `pi` / `openai-codex` / `gpt-5.6-luna`
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

1. A 报告：实现气泡与图例可访问下钻、疗效安全性产品档案抽屉、网址恢复、全空 AESI 隐藏及对应测试。
2. B 报告：实现受控临床概念/时间窗/统计形式归一化，重构疗效与基线等为跨产品试验分组图表，保留数值身份与对照组并补齐测试。
3. C 报告：实现全部设计字段的研究横向矩阵、字段组与多选筛选、单元格详情下钻，移除四字段裁剪和已公开占位压缩并补齐测试。
4. 浏览器与视觉验收：补充 1024/1280/1440/1920、键盘、抽屉、网址、图表—表格同步和中文用户任务断言，复现 R12 并验证 R13。

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
