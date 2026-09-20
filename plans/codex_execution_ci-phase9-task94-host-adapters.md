# Codex Execution Plan: ci-phase9-task94-host-adapters

Objective: 依据已批准 Task 9.4 合同，实现 Codex、Hermes、OMP 薄宿主适配一致性、宿主回执与 host-smoke-v1 合同；首版真实输出仅站点式 HTML，适配器不得改变科学真源或用静态 JSON 冒充真实宿主。

## Work Items

| Worker | Assigned item | Report |
|---|---|---|
| `worker_01` | 实现 HA01：宿主基类、共享语义/回执 Python 合同、host-receipt 双布局 Schema、包清单登记及基类越权反例测试。 | `runs/execution/ci-phase9-task94-host-adapters/worker_01.md` |
| `worker_02` | 实现 HA02–HA08：Codex/Hermes/OMP 薄适配器与三宿主语义一致、选择性能力阻断、环境恢复、手工收件箱/部分交付等价测试；复用公共 capability preflight 和事件/检查点，不复制业务逻辑。 | `runs/execution/ci-phase9-task94-host-adapters/worker_02.md` |
| `worker_03` | 实现 HA09–HA10：host-smoke-v1 fixture/catalog 摘要合同、真实入口 runner/receipt 验证器及同进程伪造、旧回执、adapter-only JSON 反例；Task 9.5 fresh-install 前不得虚报真实宿主通过。 | `runs/execution/ci-phase9-task94-host-adapters/worker_03.md` |

## Manager

No execution manager is dispatched for this route; Codex reviews the worker outputs directly.

## Codex Acceptance

TODO: verify artifacts, tests, source claims, rendered surfaces, blockers, and user-facing completeness.
