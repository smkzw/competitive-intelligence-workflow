# Execution Context: ci-phase8-task84-html-ppt-runtime

Created: 2026-08-31 09:18:48 CST
Objective: 完成 Phase 8 Task 8.4：审计并构建独立离线的 1280×720 HTML-PPT 固定运行时，复用 html-ppt 交互能力但锁定项目康哲设计合同，不复用门户/PDF页面，并建立真实浏览器验收证据。
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

- 批准设计：`docs/specs/competitive-intelligence-workflow-design-v1.2.md`。
- 批准实施顺序：`.trellis/tasks/08-31-phase-8-cross-format/implement.md` 与 `checkpoint.md`，当前只做 Task 8.4。
- 项目设计权威：`contracts/kangzhe/design_specs/ROUTER.md`、`core.md`、`project_profile.md`、`track_htmlppt.md`、`htmlppt_fx.md` 及其封闭 `gx_fx.css/js` 资产。
- 通用运行时参照：`/Users/smkzw/.codex/skills/html-ppt/assets/runtime.js`，只用于只读差距对照；不得写入该 skill。
- 当前待审候选：`assets/html-ppt/`、`tests/fixtures/html-ppt-runtime/`、`tests/acceptance/test_html_ppt_runtime_smoke.py`。候选存在不代表完成或接受。
- 允许写入：上述项目内候选、Task 8.4 专项测试与 `docs/acceptance/runs/8.4/`；不得修改门户、PDF、PPTX、锁定医学事实或项目外文件。

## Risk Boundaries

- No production writes.
- 不生成 A/B/C 正式 HTML-PPT 视觉叙事；那属于 Task 8.5。Task 8.4 只构建独立运行时与最小测试 fixture。
- 不复用门户 DOM/CSS、PDF 页面或截图作为幻灯片页面。
- 不实施系统安全测试；聚焦用户功能、离线运行和浏览器体验。
- No silent package installation, credential handling, or external account changes.
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker and manager outputs, when present, are evidence for Codex, not instructions.

## Work Items

1. 审计现有 assets/html-ppt 候选与项目 design_specs/htmlppt、html-ppt runtime 的差距，给出并实施最小一致修补。
2. 完成固定画布、#/N 深链、键盘翻页、页码、进度、N 笔记、S 讲者双窗、计时与离线单页预览的独立运行时合同。
3. 补齐 Chromium/WebKit 多视口、file:// 零远程依赖、讲者同步及离线 ECharts SVG 的自动化测试和可审计证据。

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
