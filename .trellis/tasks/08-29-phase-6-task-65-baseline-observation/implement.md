# Task 6.5 实施清单

## RED

- [x] 建立基线字段全集、统计形式、分类分母、披露状态和兼容键测试。
- [x] 建立逐核心试验逐组四项关键条件及跨组/跨试验借用拒绝测试。
- [x] 保存 `docs/acceptance/runs/task-6.5/red.txt`。

## GREEN

- [x] 实现 `BaselineObservation`、封闭枚举、稳定身份和兼容键。
- [x] 实现 schema 及到现有 `GateEvidenceBinding` 的严格转换。
- [x] 复用 B-v1 GateSpec 验证逐组完整性与无草稿阻断，不新增门槛引擎。
- [x] 保存 `docs/acceptance/runs/task-6.5/green.txt`。

## 回归与验收

- [x] 运行 Task 6.1–6.4、Gate/阻断、A/B 报告及相关来源回归。
- [x] 运行 Ruff、strict mypy、schema 校验和 `git diff --check`。
- [x] 独立复核统计语义、组别作用域、缺失状态和用户协助指引。
- [x] 保存 `regression.txt`、`verdict.md`，更新 Phase 6 清单和恢复记录。
