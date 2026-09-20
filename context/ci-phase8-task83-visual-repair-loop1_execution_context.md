# Execution Context: ci-phase8-task83-visual-repair-loop1

Created: 2026-08-31 08:37:09 CST
Objective: 修复 Task 8.3 独立视觉审阅确认的中文受众页缺陷与断行问题，重新生成三份原生 PDF 并使旧哈希失效后完成全量回归；不改医学数值、不扩展安全测试。
Task type: `visual_report_structure`
Risk: `medium`
Execution module trigger: Codex identified 3 independent work items, which is greater than two.
Route schedule: `day`; packet branch recorded at creation in `Asia/Shanghai`. Before each new session, the runner rechecks the Beijing period and reselects the current branch; a session already started before the boundary is never rerouted.
Effective worker chain: `grok-build/grok-4.6:medium -> cursor/cursor-grok-4.6:medium -> openai-codex/gpt-5.6-luna:max`

## Module Boundary

This is an execution module, not a conference. Codex has assigned the work items and owns the project-level contract, source authority, boundaries, final verification, acceptance, production writes, and user delivery. Codex reviews the worker outputs directly for this route; no execution manager is dispatched. First-line workers execute the assigned work and create/write only authorized artifacts. Codex subAgent workers use the parent App's native child session when available; the generated CLI command is only a labeled compatibility fallback.

## Assigned Roles

- First-line executor: `visual_executor` -> `grok` / `grok-build` / `grok-4.6`
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

1. 仅修改 PDF 投影中的用户文案：移除目录及 C20 的内部过程措辞，将 B 类完成情况表头改为临床医学经理可直读的中文标签；补充精确测试。
2. 仅处理 C20 支撑试验列和 C12 终点列的硬折行可读性，以及 A/B 气泡矩阵坐标语义的最小可视增强；不得改数值与数据合同。
3. 独立审阅相关测试、生成命令、哈希/页数/结构验收范围，提出并执行最小回归；不作最终视觉放行。

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
