# Codex Execution Plan: ci_phase5_a_data_matrix_recheck

Objective: 复查并修复A类特应性皮炎报告数值覆盖不足与首页/安全性页热图默认视口横向溢出，形成可追溯新产物

## Work Items

| Worker | Assigned item | Report |
|---|---|---|
| `worker_01` | 只读审计当前38个产品/43项试验从来源到默认图表的数值覆盖，逐产品定位真实未公开、来源未检索、获取失败、解析遗漏、投影遗漏和默认筛选遗漏，并写审计报告，不修改代码或数据。 | `runs/execution/ci_phase5_a_data_matrix_recheck/worker_01.md` |
| `worker_02` | 负责安全性热图显示链路：在1024/1280默认桌面视口复现首页与安全性详情页横向拖动，修复共享JS/CSS和浏览器回归测试；不得修改研究数据或数值。 | `runs/execution/ci_phase5_a_data_matrix_recheck/worker_02.md` |
| `worker_03` | 负责数值完整性数据链路：基于现有锁定来源和允许的多来源策略，修复产品/试验覆盖审计、错误结果状态或投影/默认选择逻辑，增加失败测试；不得修改门户布局CSS。 | `runs/execution/ci_phase5_a_data_matrix_recheck/worker_03.md` |

## Manager

No execution manager is dispatched for this route; Codex reviews the worker outputs directly.

## Codex Acceptance

TODO: verify artifacts, tests, source claims, rendered surfaces, blockers, and user-facing completeness.
