# Task 8.2 验收结论

日期：2026-08-31

## 结论

接受 A/B/C 三份完整原生 PDF。三份报告绑定同一 `three-report-complete` 特应性皮炎快照，文字可检索、图形为原生矢量、宽表按分页边界切换横向、书签和续表可用；未通过 HTML 或 Chromium 打印生成。

| 报告 | 页数 | SHA-256 | 交付文件 |
| --- | ---: | --- | --- |
| A 类竞品全景 | 10 | `4aa62ade74d2055a40ef740b58fb6006591f49d4209433aa15527dd8821eb1a6` | `output/pdf/A类-特应性皮炎竞品全景.pdf` |
| B 类临床试验结果 | 24 | `783485c697ab967a10e9487b6476c748da4381ba3997c66bc66b1218f9a7eb93` | `output/pdf/B类-特应性皮炎临床试验结果比较.pdf` |
| C 类临床试验设计 | 20 | `6954dfa92f05767ad92660b6e660c4baf0246cf35b6a45486b27f60487ce7b95` | `output/pdf/C类-特应性皮炎临床试验设计比较.pdf` |

## 关键事实修复

- B 类基线与完成情况原先混入另一适应症的详细视图；已从根因处清除。无本适应症可信来源支持的数值全部保留为“未公开”，不以错误数字或零填充。
- 计划样本量与已披露基线分析/受试者流转人数分别说明；B24 的疗效与安全性覆盖补齐组别列。
- C 类访视图改为 0/16/24/52 周真实横轴与四试验泳道，不再使用 A–H 假时间线。
- A/B 疗效柱状图、组间差值图与解释文字不再重叠；三份封面的截止日期改为中文日期。

## 验收证据

- Ruff 通过；`tests/pdf` 22 项通过；PDF 与 fixture 合同组合 26 项通过。
- `docs/acceptance/runs/8.2/verification/summary.json`：A10/B24/C20 均 `coverage_ok=true`、`defect_count=0`。
- 点名测试者沿用原会话完成第二轮复验：`pi/cms-router/minimax-m3`、`pi/cursor/cursor-grok-4.6:medium`、`codebuddy/hy3-x:max`，三条路线无 fallback。
- 正式视觉终审沿用会话 `01a05425-2e14-7000-a169-cdcf911e88c2` 完成第六轮，接受最终哈希。
- `hermes_workflow_guard.py audit-execution` 返回 `ok=true`。

## 非阻断后续

目录页码、个别高密度窄列折行、气泡贴近绘图区边框可在后续版本继续精修；当前不存在会导致错适应症、错试验、错数值、关键时间点误读或报告不可读的缺陷。
