# Codex Execution Plan: ci-phase8-task86-visual-baseline

Objective: 建立 A/B/C 共62页 HTML-PPT 的全页多视口真实渲染证据、自动缺陷台账和首轮可读性修订基线；不改变锁定医学数据，不做安全测试。

## Work Items

| Worker | Assigned item | Report |
|---|---|---|
| `worker_01` | 设计并实现最小可复用的全页多视口 Chromium/WebKit 原图与诊断收集器，绑定当前三个 HTML 哈希，输出中文台账。 | `runs/execution/ci-phase8-task86-visual-baseline/worker_01.md` |
| `worker_02` | 只读审查三份当前 HTML 的 62 页视觉与医学经理可读性，重点定位标签、数值、图例、留白、内容密度和中文表达缺陷并提供页级证据。 | `runs/execution/ci-phase8-task86-visual-baseline/worker_02.md` |
| `worker_03` | 复核 Task 8.6 的康哲设计合同、实际显示器视口、离线运行时和逐页验收标准，提出可执行的验收矩阵与失败关闭条件。 | `runs/execution/ci-phase8-task86-visual-baseline/worker_03.md` |

## Manager

No execution manager is dispatched for this route; Codex reviews the worker outputs directly.

## Codex Acceptance

TODO: verify artifacts, tests, source claims, rendered surfaces, blockers, and user-facing completeness.
