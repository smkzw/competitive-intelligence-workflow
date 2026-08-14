# Phase 5 A 类门户实施清单

## Task 5.2

- [x] AV01 竞争格局保留全部产品与全部分组维度。
- [x] AV02 产品总览完整、可筛选且无 Top-N。
- [x] AV03 每个产品有完整档案与稳定路由。
- [x] AV04 临床组合保留产品、试验、地域、阶段和状态。
- [x] AV05 中国与境外监管事件分开且版本化。
- [x] AV06 企业关系、地域权益与交易条款不混写。
- [x] AV07 专利族、法域、期限与监管独占分开。
- [x] AV08 暂停、终止、撤回、放弃和边缘观察不消失。
- [x] `uv run pytest tests/unit/reports/a -q`（219 passed）。
- [x] A 专项、共享证据交叉和全仓回归（310 / 527 / 1047 passed）。
- [x] Ruff、strict mypy、独立审查与任务记录。
- [x] 提交：`feat: add full report A profile and landscape views`

实现顺序严格采用计划 AV01–AV08；每个节点先看到失败，再做最小实现并原样复验。Task 5.2 不生成模板或产物。

## 暂停点

Task 5.2 已由 Luna 第五轮独立验收为 `PASS`（P0/P1/P2 均为 0）。按用户要求，提交后在 Task 5.3 开始前无损暂停；恢复时先读取 `context/ci_phase5_task52_context.md` 和本文件，不重做 5.2。
