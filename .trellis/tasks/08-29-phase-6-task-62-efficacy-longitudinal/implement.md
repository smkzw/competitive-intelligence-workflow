# Task 6.2 实施清单

## RED

- [x] 建立指南依据的三项具名合同测试，并如实记录初始实现与计划合同之间的缺口。
- [x] 建立单时间点、纵向、来源效应量视图及治疗—对照并列测试。
- [x] 建立默认不排名、兼容桶内排序、未知非零和重置测试。
- [x] 保存 `docs/acceptance/runs/task-6.2/red.txt`。

## GREEN

- [x] 在 `src/ci_workflow/reports/b/efficacy.py` 实现指南/竞品终点依据。
- [x] 实现三类疗效视图模型，共用稳定事实行与来源谱系。
- [x] 实现确定性默认顺序和可逆用户排序。
- [x] 保存 `docs/acceptance/runs/task-6.2/green.txt`。

## 回归与验收

- [x] 运行 Task 6.1、B 报告、A 报告及 PubMed/ClinicalTrials.gov 相关回归。
- [x] 运行 Ruff、strict mypy、`git diff --check`。
- [x] 独立复核指南状态、竞品分母、组别并列、兼容桶和未知值边界。
- [x] 保存 `regression.txt`、`verdict.md`，更新 Phase 6 清单和恢复记录。
