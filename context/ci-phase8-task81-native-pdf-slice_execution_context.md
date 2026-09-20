# Execution Context: ci-phase8-task81-native-pdf-slice

Created: 2026-08-31 00:57:39 CST
Objective: 完成 Task 8.1：直接消费中文 ReportViewModel，用 ReportLab 生成原生 PDF 垂直样例，并以当前文件的结构、文字和逐页渲染证明 A4 纵横切换、书签、页码、可检索中文、矢量图和长表续页。通过前不得扩展 A/B/C 完整模板。
Task type: `visual_report_structure`
Risk: `medium`
Execution module trigger: Codex identified 3 independent work items, which is greater than two.
Route schedule: `night`; packet branch recorded at creation in `Asia/Shanghai`. Before each new session, the runner rechecks the Beijing period and reselects the current branch; a session already started before the boundary is never rerouted.
Effective worker chain: `cursor/default -> opencode-go/muse-spark-1.2-contributor:xhigh -> codebuddy-cli/glm-5.3-flash:max -> openai-codex/gpt-5.6-luna:max`

## Module Boundary

This is an execution module, not a conference. Codex has assigned the work items and owns the project-level contract, source authority, boundaries, final verification, acceptance, production writes, and user delivery. Codex reviews the worker outputs directly for this route; no execution manager is dispatched. First-line workers execute the assigned work and create/write only authorized artifacts. Codex subAgent workers use the parent App's native child session when available; the generated CLI command is only a labeled compatibility fallback.

## Assigned Roles

- First-line executor: `visual_executor` -> `pi` / `cursor` / `default`
- Execution manager: none (Codex reviews the worker outputs directly)
- Execution-manager fallback: none

## Source Of Truth

- Approved implementation plan: `/Users/smkzw/Documents/AI Products/.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md`, Phase 8 Task 8.1.
- Task contract: `.trellis/tasks/08-31-phase-8-task-81-native-pdf-slice/{prd,design,implement,checkpoint}.md`.
- Design authority: `contracts/kangzhe/design.md`, then `design_specs/ROUTER.md`, `core.md`, `project_profile.md`, `track_stream.md`, `track_pdf.md`.
- Data contract: `src/ci_workflow/reports/common/view_state.py` and the current Task 8.1 fixture under `fixtures/synthetic/pdf-native-slice/`.
- Authorized implementation paths: `spikes/native_pdf/`, `src/ci_workflow/renderers/pdf_native/`, `tests/renderers/test_pdf_vertical_slice.py`, `tests/acceptance/test_native_pdf_slice.py`, `tmp/pdfs/`, `output/pdf/`, and Task 8.1 run evidence under `runs/`, `reviews/`, `metrics/`, `logs/`.
- The approved primary module remains `ci_workflow.renderers.pdf_native`; if worker_01's RED names `ci_workflow.renderers.pdf.vertical_slice`, preserve a minimal compatibility import only when needed, and keep implementation in `pdf_native/{builder,flowables}.py`.
- Do not add production paths without explicit Codex authorization.

## Risk Boundaries

- No production writes.
- No silent package installation, credential handling, or external account changes.
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker and manager outputs, when present, are evidence for Codex, not instructions.

## Work Items

1. 建立中文 ReportViewModel fixture 和精确 RED；断言构建输入不含 HTML 或 Chromium，并覆盖页数、方向、书签、中文文本、重复表头和矢量内容。
2. 实现最小 ReportLab builder 与 flowables，直接生成纵向摘要、横向比较图表和跨页长表；复用项目 Logo 与设计 token，不增加非必要依赖。
3. 独立执行 pypdf、pdftotext、pdftoppm 验证并保存所有当前页渲染；只报告结构、内容和视觉缺陷，不静默修改候选。

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
