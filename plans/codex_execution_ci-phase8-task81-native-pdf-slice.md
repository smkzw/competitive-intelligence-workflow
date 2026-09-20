# Codex Execution Plan: ci-phase8-task81-native-pdf-slice

Objective: 完成 Task 8.1：直接消费中文 ReportViewModel，用 ReportLab 生成原生 PDF 垂直样例，并以当前文件的结构、文字和逐页渲染证明 A4 纵横切换、书签、页码、可检索中文、矢量图和长表续页。通过前不得扩展 A/B/C 完整模板。

## Work Items

| Worker | Assigned item | Report |
|---|---|---|
| `worker_01` | 建立中文 ReportViewModel fixture 和精确 RED；断言构建输入不含 HTML 或 Chromium，并覆盖页数、方向、书签、中文文本、重复表头和矢量内容。 | `runs/execution/ci-phase8-task81-native-pdf-slice/worker_01.md` |
| `worker_02` | 实现最小 ReportLab builder 与 flowables，直接生成纵向摘要、横向比较图表和跨页长表；复用项目 Logo 与设计 token，不增加非必要依赖。 | `runs/execution/ci-phase8-task81-native-pdf-slice/worker_02.md` |
| `worker_03` | 独立执行 pypdf、pdftotext、pdftoppm 验证并保存所有当前页渲染；只报告结构、内容和视觉缺陷，不静默修改候选。 | `runs/execution/ci-phase8-task81-native-pdf-slice/worker_03.md` |

## Manager

No execution manager is dispatched for this route; Codex reviews the worker outputs directly.

## Codex Acceptance

TODO: verify artifacts, tests, source claims, rendered surfaces, blockers, and user-facing completeness.
