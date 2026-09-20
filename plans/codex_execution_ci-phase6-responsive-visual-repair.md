# Codex Execution Plan: ci-phase6-responsive-visual-repair

Objective: 修复并验证当前B类PNH报告在768视口的数据表可发现性、折叠菜单搜索聚焦与Escape关闭语义，重新生成可审计视觉证据

## Work Items

| Worker | Assigned item | Report |
|---|---|---|
| `worker_01` | 以独立测试者身份复现三项视觉会商阻断，先补充失败测试，覆盖Chromium与WebKit的768表格、菜单搜索聚焦和真实Escape行为；只改测试 | `runs/execution/ci-phase6-responsive-visual-repair/worker_01.md` |
| `worker_02` | 基于失败测试做最小实现修复：768数据表改为无需横拖即可读的堆叠呈现，菜单展开聚焦搜索，Escape可靠关闭且不被input事件重开；只改实现与必要静态资产清单 | `runs/execution/ci-phase6-responsive-visual-repair/worker_02.md` |
| `worker_03` | 在修复后生成新候选与视觉证据，运行Chromium/WebKit三宽度浏览器验收并检查其余B类页面复用组件；不得接受未运行的结果 | `runs/execution/ci-phase6-responsive-visual-repair/worker_03.md` |

## Manager

No execution manager is dispatched for this route; Codex reviews the worker outputs directly.

## Codex Acceptance

TODO: verify artifacts, tests, source claims, rendered surfaces, blockers, and user-facing completeness.
