# Execution Context: ci-phase8-task86-visual-baseline

Created: 2026-08-31 12:40:17 CST
Objective: 建立 A/B/C 共62页 HTML-PPT 的全页多视口真实渲染证据、自动缺陷台账和首轮可读性修订基线；不改变锁定医学数据，不做安全测试。
Task type: `html_ppt_visual_browser`
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

1. 设计并实现最小可复用的全页多视口 Chromium/WebKit 原图与诊断收集器，绑定当前三个 HTML 哈希，输出中文台账。
2. 只读审查三份当前 HTML 的 62 页视觉与医学经理可读性，重点定位标签、数值、图例、留白、内容密度和中文表达缺陷并提供页级证据。
3. 复核 Task 8.6 的康哲设计合同、实际显示器视口、离线运行时和逐页验收标准，提出可执行的验收矩阵与失败关闭条件。

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
