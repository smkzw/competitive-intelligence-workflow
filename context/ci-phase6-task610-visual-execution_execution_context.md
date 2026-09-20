# Execution Context: ci-phase6-task610-visual-execution

Created: 2026-08-30 10:25:01 CST
Objective: 以真实医学经理视角对 B 类 PNH 当前候选门户完成视觉、交互、数值一致性和默认视野可读性执行检查；只读，不修改候选物
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

- Current candidate site: `output/acceptance/task-6.10/b-pnh-current-v8/reports/B/v-fixture-b-pnh-001/html/`.
- Candidate input: `fixtures/positive/b-pnh/inputs/report-data.json`.
- Project visual contract: `contracts/kangzhe/design_specs/project_profile.md`, `contracts/kangzhe/design_specs/core.md`, and `contracts/kangzhe/design_specs/track_interactive.md`.
- Browser acceptance contract: `tests/browser/test_b_portal.py`.
- Existing rendered screenshots may be used only as supporting evidence: `output/playwright/task-6.10-current/`; reviewers must still exercise the live local HTML with real browser and visual capabilities.
- Do not add production paths without explicit Codex authorization.

## Risk Boundaries

- No production writes.
- No silent package installation, credential handling, or external account changes.
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker and manager outputs, when present, are evidence for Codex, not instructions.

## Work Items

1. 在 1024、1280、1440 宽度真实浏览首页与疗效安全性矩阵，核对首屏、坐标、气泡、表格和无横向拖动
2. 在 1024、1280、1440 宽度真实浏览安全性页，核对热图治疗组与对照组、数值、缺失状态和无横向拖动
3. 完成首页到筛选、图表、完整数据表、数据依据、产品和试验档案下钻再返回的真实使用路径，审阅中文原生性和信息密度

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
