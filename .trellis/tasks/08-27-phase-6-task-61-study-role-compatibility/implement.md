# Task 6.1 实施清单

## 2026-08-27 插入式暂停

用户验收上一阶段 A 类报告时发现两项 P0 用户问题：大量疗效/安全性数值缺失，以及首页和安全性页热图必须横向拖动。Task 6.1 的三个受控执行工作项已经返回，代码与报告仍保留在工作树中，尚未经过 Codex 终验、回归、提交或完成标记。当前先修复 A 类已交付纵切；恢复 Task 6.1 时必须从现有工作树和 `runs/execution/ci_phase6_task61_execution/` 继续，不得重新派发或把执行者自报当成验收。

## RED

- [x] 在 `tests/reports/test_study_role_policy.py` 建立研究角色最小合同及计划指定的五个具名测试。
- [x] 在 `tests/reports/b/test_trial_roles.py` 建立 B 角色输出、规则谱系及论文角色分离合同。
- [x] 在 `tests/reports/b/test_endpoint_compatibility.py` 建立终点/时间窗兼容与越界分列合同。
- [x] 原样运行三份测试，确认失败来自目标实现缺失或行为不满足。
- [x] 保存 `docs/acceptance/runs/task-6.1/red.txt`。

## GREEN

- [x] 实现 `reports/common/study_roles.py` 和 `policies/studies/study-role-v1.yaml`。
- [x] 实现 `reports/b/contracts.py`、`policies/endpoints/compatibility-v1.yaml`、`policies/timepoints/compatibility-v1.yaml`。
- [x] 原样重跑三份测试并保存 `green.txt`。

## 回归与验收

- [x] 运行 A/B 共用报告与 PubMed/ClinicalTrials.gov 相关回归。
- [x] 运行 Ruff、strict mypy、`git diff --check`。
- [x] 独立验证研究角色排除边界、论文角色不覆盖及终点越界分列。
- [x] 保存 `regression.txt`、`verdict.md`，更新 Phase 6 实施清单；未把当前脏工作树中其他阶段改动混入提交。
