# Task 8.1 检查点

记录日期：2026-08-31

## 当前状态

Task 8.1 已完成并通过 Codex 最终验收。系统直接消费中文 `ReportViewModel`，用 ReportLab 生成 4 页 A4 原生 PDF：纵向摘要、横向疗效图表、两页纵向安全性长表。疗效柱状图为原生矢量，中文文字可选择检索，书签、页码、嵌入中文字体、纵横页切换、续表表头和临床语境均已验证。

最终 `tmp/pdfs/` 与 `output/pdf/` 文件字节一致，SHA-256 为 `b32d7c390ec3d456a5b47c63f996537c360ce7ac0bb3068784c624ed8e9cbbbe`。当前四页渲染保存在同摘要命名的 review 目录。8 项专项测试与 Ruff 通过；正式视觉会商经同一 Cursor Grok 会话完成三轮，三条用户点名路线 Minimax M3、Cursor Grok 4.6 medium、Hy3-x 均独立通过 Task 8.1 样例门槛。

## 已确认边界

- 输入必须是结构化 `ReportViewModel`，不得经过 HTML 或 Chromium。
- 候选中间文件进入 `tmp/pdfs/`，通过后正式样例进入 `output/pdf/`；两者当前摘要必须一致。
- 未完成结构、文字、逐页渲染和隔离视觉验收前，不扩展 A/B/C 完整模板。

## 下一安全动作

进入 Task 8.2：先建立唯一的 `three-report-complete` A/B/C 四格式基准 fixture 与逐文件摘要绑定，再按 PDF01–PDF09 微任务扩展完整原生 PDF。不得把本 4 页样例或其留白裁决误称为完整 A/B/C PDF 已完成；Task 8.2 仍需执行全量高信息密度和逐页视觉验收。
