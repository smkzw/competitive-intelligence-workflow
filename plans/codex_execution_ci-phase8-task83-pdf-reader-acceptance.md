# Codex Execution Plan: ci-phase8-task83-pdf-reader-acceptance

Objective: 对 Task 8.2 已接受且哈希锁定的 A/B/C 原生 PDF 建立只读验收合同，生成逐页文本、原始页图与 contact sheet，在标准 PDF 阅读器与独立视觉审阅中完成全部 54 页验收；不得修改 PDF 医学内容，不启动 HTML-PPT/PPTX。

## Work Items

| Worker | Assigned item | Report |
|---|---|---|
| `worker_01` | 实现 src/ci_workflow/qc/pdf.py 只读 PDF 验收模型：绑定报告、最终 SHA-256、页数、逐页文本/方向/页眉页脚/页码/续表/原图证据并失败关闭；不得改写被验收产物。 | `runs/execution/ci-phase8-task83-pdf-reader-acceptance/worker_01.md` |
| `worker_02` | 扩展 tools/verify_pdf.py，复用 pypdf、pdftotext、pdftoppm 与现有 coverage projection，生成逐页文本、当前原始页图、contact sheet、结构化证据与哈希绑定；不增加新依赖。 | `runs/execution/ci-phase8-task83-pdf-reader-acceptance/worker_02.md` |
| `worker_03` | 新增 tests/acceptance/test_pdf_outputs.py，对最终 A10/B24/C20 PDF 精确验证打开、中文检索、书签、页码、A4方向、页眉页脚、续表、逐页证据、contact sheet 和不可变哈希，并运行最小到相关回归测试。 | `runs/execution/ci-phase8-task83-pdf-reader-acceptance/worker_03.md` |

## Manager

No execution manager is dispatched for this route; Codex reviews the worker outputs directly.

## Codex Acceptance

TODO: verify artifacts, tests, source claims, rendered surfaces, blockers, and user-facing completeness.
