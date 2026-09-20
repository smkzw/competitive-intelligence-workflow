# Task 6.3 实施清单

## RED

- [x] 建立披露状态、数值一致性、阈值与技术异常测试并确认真实失败原因。
- [x] 建立默认维度、同事件可比色阶、组别并列与多试验分列测试。
- [x] 建立常见事件默认选择、完整搜索展开、术语映射与无排名测试。
- [x] 保存 `docs/acceptance/runs/task-6.3/red.txt`。

## GREEN

- [x] 在 `src/ci_workflow/reports/b/safety.py` 实现安全性事实、可比语境和披露状态合同。
- [x] 实现多维热图与完整 AE 视图模型。
- [x] 实现确定性默认事件选择和完整事件搜索/展开。
- [x] 保存 `docs/acceptance/runs/task-6.3/green.txt`。

## 回归与验收

- [x] 运行 Task 6.1–6.2、B 报告、A 报告及相关来源回归。
- [x] 运行 Ruff、strict mypy、`git diff --check`。
- [x] 独立复核披露状态、色阶可比性、默认事件选择和无排名边界。
- [x] 保存 `regression.txt`、`verdict.md`，更新 Phase 6 清单和恢复记录。
