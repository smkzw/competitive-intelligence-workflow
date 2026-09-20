# Codex Execution Plan: ci-phase8-task83-visual-repair-loop1

Objective: 修复 Task 8.3 独立视觉审阅确认的中文受众页缺陷与断行问题，重新生成三份原生 PDF 并使旧哈希失效后完成全量回归；不改医学数值、不扩展安全测试。

## Work Items

| Worker | Assigned item | Report |
|---|---|---|
| `worker_01` | 仅修改 PDF 投影中的用户文案：移除目录及 C20 的内部过程措辞，将 B 类完成情况表头改为临床医学经理可直读的中文标签；补充精确测试。 | `runs/execution/ci-phase8-task83-visual-repair-loop1/worker_01.md` |
| `worker_02` | 仅处理 C20 支撑试验列和 C12 终点列的硬折行可读性，以及 A/B 气泡矩阵坐标语义的最小可视增强；不得改数值与数据合同。 | `runs/execution/ci-phase8-task83-visual-repair-loop1/worker_02.md` |
| `worker_03` | 独立审阅相关测试、生成命令、哈希/页数/结构验收范围，提出并执行最小回归；不作最终视觉放行。 | `runs/execution/ci-phase8-task83-visual-repair-loop1/worker_03.md` |

## Manager

No execution manager is dispatched for this route; Codex reviews the worker outputs directly.

## Codex Acceptance

TODO: verify artifacts, tests, source claims, rendered surfaces, blockers, and user-facing completeness.
