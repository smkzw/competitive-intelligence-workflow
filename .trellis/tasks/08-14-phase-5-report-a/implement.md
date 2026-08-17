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

## Task 5.3

- [x] AS01 确定性锚定试验与按靶点分组的疗效治疗组/对照组比较。
- [x] AS02 多维安全性热图保留事件、时间窗、分母、组别和披露状态。
- [x] AS03 疗效—安全性气泡图使用方向校正疗效、倒序原始 TEAE 与 `r=k×sqrt(N/pi)`，且不含综合分数或默认名次。
- [x] 当前快照、完整产品集、事实版本、内容摘要及 `model_copy` 篡改反例闭合。
- [x] `tests/reports/a/test_efficacy_safety_summary.py`、`test_bubble_matrix.py` 先红后绿；A 专项、共享回归、Ruff、strict mypy及独立反证验收通过。

验收证据：53 项 Task 5.3 定向契约、363 项 A 类组合、1387 项全工程回归通过；Ruff、strict mypy、`git diff --check` 通过；Luna 同一独立会话连续反证并最终给出 `PASS（P0/P1/P2=0）`。本步只有数据合同，不以空壳页面冒充视觉验收；真实医学经理视觉试用继续留在 Task 5.4/5.5。
