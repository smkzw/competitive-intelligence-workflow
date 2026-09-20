# Codex Execution Plan: ci_phase5_a_result_visibility_repair

Objective: 修复 A 类报告来源结果漏投影和首页/安全性页热图横向溢出，重新建立来源完整性与默认可见性验收

## Work Items

| Worker | Assigned item | Report |
|---|---|---|
| `worker_01` | 实现并测试 ClinicalTrials.gov 结果覆盖审计：识别来源已有但报告遗漏的结局与逐事件 AE，严格区分 TEAE、SAE、AESI、常见 AE 和解析失败 | `runs/execution/ci_phase5_a_result_visibility_repair/worker_01.md` |
| `worker_02` | 修复并测试首页与安全性页热图：转置产品/事件布局，1280px 默认视野无矩阵横向滚动且全量产品可纵向查看 | `runs/execution/ci_phase5_a_result_visibility_repair/worker_02.md` |
| `worker_03` | 建立特应性皮炎研究包重建工具与回归：从包内锁定来源补齐可解析疗效和安全性事实、重算摘要并生成可复现产物 | `runs/execution/ci_phase5_a_result_visibility_repair/worker_03.md` |

## Manager

No execution manager is dispatched for this route; Codex reviews the worker outputs directly.

## Codex Acceptance

已完成：验证锁定来源、研究包、正式 fresh 运行、报告快照、双浏览器三视口、6 事件交互、关键 n/N、科学复核与视觉复核。Ruff、mypy、`git diff --check` 及全工程 1,475 项测试通过。本次两项修复接受。
