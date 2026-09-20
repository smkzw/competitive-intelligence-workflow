# Codex Execution Plan: ci-phase6-interaction-repair

Objective: 修复B类报告证据单元格键盘运行错误和Chromium搜索Esc重开缺陷，补充回归并重建当前PNH候选

## Work Items

| Worker | Assigned item | Report |
|---|---|---|
| `worker_01` | 以RED测试复现证据单元格Enter/Space触发未定义函数的运行错误 | `runs/execution/ci-phase6-interaction-repair/worker_01.md` |
| `worker_02` | 修复证据单元格键盘激活与全局搜索Esc关闭一致性，保持鼠标和其他交互不回归 | `runs/execution/ci-phase6-interaction-repair/worker_02.md` |
| `worker_03` | 运行跨内核交互回归并从原fixture生成新的持久化PNH候选与摘要 | `runs/execution/ci-phase6-interaction-repair/worker_03.md` |

## Manager

No execution manager is dispatched for this route; Codex reviews the worker outputs directly.

## Codex Acceptance

TODO: verify artifacts, tests, source claims, rendered surfaces, blockers, and user-facing completeness.
