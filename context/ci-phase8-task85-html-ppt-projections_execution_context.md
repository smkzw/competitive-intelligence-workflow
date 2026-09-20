# Execution Context: ci-phase8-task85-html-ppt-projections

Created: 2026-08-31 10:03:01 CST
Objective: 完成 Task 8.5：基于 A/B/C 当前锁定结构化报告数据生成三份独立、单文件、离线、康哲母版化 HTML-PPT；复用 Task 8.4 运行时并原样注入项目 FX，包含中文演讲者视图和每页 150–300 字逐字稿；建立可重跑结构/浏览器合同，不复用门户或 PDF 截图。
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

- 产品边界：`.trellis/tasks/08-31-phase-8-task-85-html-ppt-projections/{prd,design,implement,checkpoint}.md`。
- 康哲 HTML-PPT 唯一权威：`contracts/kangzhe/design_specs/ROUTER.md`、`core.md`、`project_profile.md`、`track_htmlppt.md`、`htmlppt_fx.md`、`assets/logo_bot.svg`、`assets/htmlppt/gx_fx.css`、`assets/htmlppt/gx_fx.js`。
- 固定运行时：`assets/html-ppt/runtime.js`、`runtime.css`、`manifest.json`；Task 8.4 结论：`docs/acceptance/runs/8.4/verdict.md`。
- A 内容：`fixtures/positive/a-atopic-dermatitis/research-content.json`、`research-package.json`。
- B 内容：`fixtures/positive/b-pnh/inputs/report-data.json`。
- C 内容：`fixtures/positive/c-atopic-dermatitis/inputs/report-data.json`。
- 页面责任与覆盖：`src/ci_workflow/reports/common/page_registry.py`、`fixtures/synthetic/three-report-complete/inputs/coverage-set-expected.json`。
- PDF 投影仅用于核对当前数据与章节覆盖：`src/ci_workflow/renderers/pdf_native/projections/`；禁止复用 PDF 布局、流式分页或截图。
- 现有 HTML-PPT 运行时样例只用于交互合同：`tests/fixtures/html-ppt-runtime/index.html`；其极简视觉不是正式母版。
- Do not add production paths without explicit Codex authorization.

## Authorized Writes

- `worker_01`：只可写 `docs/acceptance/runs/8.5/projection-contract.md` 和 `tests/html_ppt/test_projection_contract.py`。
- `worker_02`：只可写 `src/ci_workflow/renderers/html_ppt/`中共享组装/组件/图表/A 投影文件、`tools/render_html_ppt.py`、`tests/html_ppt/test_report_a_html_ppt.py` 以及 `output/html-ppt/`中 A 候选。
- `worker_03`：只可写 `src/ci_workflow/renderers/html_ppt/`中 B/C 投影及必要的最小共享修补、`tools/render_html_ppt.py`、`tests/html_ppt/`、`output/html-ppt/`、`docs/acceptance/runs/8.5/`。
- 不得修改锁定输入、门户、PDF、Task 8.4 运行时、项目设计规范或其他阶段文件。

## Deterministic Acceptance Anchors

- 输出必须是单 HTML 文件，Logo/CSS/JS/runtime/FX 全部内联，源码不得含外链资源属性。
- 每个 `.slide` 的逻辑尺寸固定 1280×720；不使用 viewport 字号/页内媒体重排。
- 每页一个 `aside.notes`，可见中文文案不得含工程/日志/prompt 语言，逐字稿必须为 150–300 个中文字符并含 `<strong>`。
- 三份 deck 的主题页必须是当前数据驱动，不得以空卡、统一“未公开”或系统内部说明冒充内容。
- Task 8.5 至少验证结构、离线、运行时、逐字稿、字号和报告覆盖；最大化窗口逐页视觉终验不得在本步代替 Task 8.6。

## Risk Boundaries

- No production writes.
- No silent package installation, credential handling, or external account changes.
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker and manager outputs, when present, are evidence for Codex, not instructions.

## Work Items

1. 审计 A/B/C 当前锁定结构化输入、页面责任和报告型叙事，形成可实现的三份 deck 结构与数据映射，并建立失败关闭合同。
2. 实现共享 HTML-PPT 单文件组装器、康哲母版/FX/Logo/运行时内联和 A 类视觉叙事投影，保持 1280×720 固定画布与中文原生文案。
3. 实现 B/C 类完整视觉叙事投影及 Task 8.5 结构、离线、逐字稿、字号、覆盖和真实浏览器基础测试，生成三份当前候选与清单。

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
