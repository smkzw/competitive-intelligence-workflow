# Execution Context: ci-phase8-task83-pdf-reader-acceptance

Created: 2026-08-31 05:47:21 CST
Objective: 对 Task 8.2 已接受且哈希锁定的 A/B/C 原生 PDF 建立只读验收合同，生成逐页文本、原始页图与 contact sheet，在标准 PDF 阅读器与独立视觉审阅中完成全部 54 页验收；不得修改 PDF 医学内容，不启动 HTML-PPT/PPTX。
Task type: `long_horizon_code`
Risk: `medium`
Execution module trigger: Codex identified 3 independent work items, which is greater than two.
Route schedule: `unscheduled`; packet branch recorded at creation in `Asia/Shanghai`. Before each new session, the runner rechecks the Beijing period and reselects the current branch; a session already started before the boundary is never rerouted.
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

1. 实现 src/ci_workflow/qc/pdf.py 只读 PDF 验收模型：绑定报告、最终 SHA-256、页数、逐页文本/方向/页眉页脚/页码/续表/原图证据并失败关闭；不得改写被验收产物。
2. 扩展 tools/verify_pdf.py，复用 pypdf、pdftotext、pdftoppm 与现有 coverage projection，生成逐页文本、当前原始页图、contact sheet、结构化证据与哈希绑定；不增加新依赖。
3. 新增 tests/acceptance/test_pdf_outputs.py，对最终 A10/B24/C20 PDF 精确验证打开、中文检索、书签、页码、A4方向、页眉页脚、续表、逐页证据、contact sheet 和不可变哈希，并运行最小到相关回归测试。

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
