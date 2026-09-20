# Execution Context: ci_phase5_a_data_matrix_recheck

Created: 2026-08-28 01:13:22
Objective: 复查并修复A类特应性皮炎报告数值覆盖不足与首页/安全性页热图默认视口横向溢出，形成可追溯新产物
Task type: `long_horizon_code`
Risk: `high`
Execution module trigger: Codex identified 3 independent work items, which is greater than two.

## Module Boundary

This is an execution module, not a conference. Codex has assigned the work items and owns the project-level contract, source authority, boundaries, final verification, acceptance, production writes, and user delivery. Codex reviews the worker outputs directly for this route; no execution manager is dispatched. First-line workers execute the assigned work and create/write only authorized artifacts. Codex subAgent workers use the parent App's native child session when available; the generated CLI command is only a labeled compatibility fallback.

## Assigned Roles

- First-line executor: `long_horizon_code_executor_opencode_flash` -> `codex-subagent` / `codex` / `gpt-5.6-luna`
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

1. 只读审计当前38个产品/43项试验从来源到默认图表的数值覆盖，逐产品定位真实未公开、来源未检索、获取失败、解析遗漏、投影遗漏和默认筛选遗漏，并写审计报告，不修改代码或数据。
2. 负责安全性热图显示链路：在1024/1280默认桌面视口复现首页与安全性详情页横向拖动，修复共享JS/CSS和浏览器回归测试；不得修改研究数据或数值。
3. 负责数值完整性数据链路：基于现有锁定来源和允许的多来源策略，修复产品/试验覆盖审计、错误结果状态或投影/默认选择逻辑，增加失败测试；不得修改门户布局CSS。

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
