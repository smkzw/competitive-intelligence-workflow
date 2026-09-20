# Codex Execution Plan: ci-r2-bc-research-package-wiring-20260905

Objective: 为 B/C 建立与 A 等价但不复制 A 门户模型的类型化 fresh-source research package、证据谱系、逐报告 GateSpec、不可变快照和独立科学 QC 绑定；保留 report-data 快捷路径为 rendered_unreviewed，并由 Codex 后续集成 RunService。

## Work Items

| Worker | Assigned item | Report |
|---|---|---|
| `worker_01` | 设计并实现共享的 report-agnostic fresh research package、来源/事实/声明/独立科学复核绑定与持久化谱系原语；新模块优先、TDD、不得修改 run_service.py 或 A 现有合同。 | `runs/execution/ci-r2-bc-research-package-wiring-20260905/worker_01.md` |
| `worker_02` | 设计并实现 B 类 fresh-source package 的类型化内容、完整医学语义字段、基线/疗效/安全/处置 GateSpec 评估、独立 QC 摘要绑定与 B 报告快照投影；TDD，限制在 B 新模块与对应测试，不修改共享或 run_service.py。 | `runs/execution/ci-r2-bc-research-package-wiring-20260905/worker_02.md` |
| `worker_03` | 设计并实现 C 类 fresh-source package 的类型化内容、登记优先设计事实/入排/终点/干预 GateSpec、多路径非排名约束、独立 QC 摘要绑定与 C 报告快照投影；TDD，限制在 C 新模块与对应测试，不修改共享或 run_service.py。 | `runs/execution/ci-r2-bc-research-package-wiring-20260905/worker_03.md` |

## Manager

No execution manager is dispatched for this route; Codex reviews the worker outputs directly.

## Codex Acceptance

Codex will diff every isolated clone against its dispatch baseline, reject duplicated or A-specific abstractions that do not satisfy v1.3, select one shared API, and apply only coherent patches with `apply_patch`. Codex then writes the real `RunService` integration, adds cross-report negative/recovery/idempotency tests, reruns Ruff/strict-mypy/unit/contract/integration, and initializes a separate clean-context science conference. Worker reports cannot mark R2 complete.
