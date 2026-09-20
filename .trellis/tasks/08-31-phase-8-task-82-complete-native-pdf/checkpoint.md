# Task 8.2 检查点

记录日期：2026-08-31

## 当前状态

Task 8.2 已完成并接受。`three-report-complete` 锁定同一特应性皮炎快照，A/B/C 三份报告均由 ReportLab 原生生成，不经 HTML/Chromium。

- A：10 页，SHA-256 `4aa62ade74d2055a40ef740b58fb6006591f49d4209433aa15527dd8821eb1a6`
- B：24 页，SHA-256 `783485c697ab967a10e9487b6476c748da4381ba3997c66bc66b1218f9a7eb93`
- C：20 页，SHA-256 `6954dfa92f05767ad92660b6e660c4baf0246cf35b6a45486b27f60487ce7b95`

关键修复：B 类跨适应症详细视图污染已清除，缺乏本适应症证据的基线与完成字段统一保留为“未公开”；计划样本量与分析/流转人数分开说明；B24 补齐组别；C 访视改为真实周数轴和分试验泳道；A/B 疗效图标签、刻度和解释不再重叠；三份封面使用中文截止日期。

验收锚点：`docs/acceptance/runs/8.2/verification/summary.json` 为全绿，Ruff 通过，PDF 测试 22 项与 PDF+fixture 测试 26 项通过；三条点名路线沿用原会话复验且无 fallback；正式视觉终审第六轮接受最终哈希；`audit-execution` 通过。早期未登记补发提示和旧核验目录均已可恢复归档。

## 下一安全动作

进入 Task 8.3：基于上述不可变 PDF 哈希实现 PDF 阅读器与逐页验收，不修改 Task 8.2 的医学事实或已接受原生 PDF；任何修订须生成新版本并重新绑定哈希。
