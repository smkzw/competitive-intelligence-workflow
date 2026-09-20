# Codex Execution Plan: ci-r2-capability-execution-gate-20260905

Objective: 独立审查并验证核心 capability matrix 的持久化、不可复用预检与按研究/HTML 交付选择性阻断合同，给 Codex 提供可执行缺口和验收结论

## Work Items

| Worker | Assigned item | Report |
|---|---|---|
| `worker_01` | 追踪 run_service 全路径并审查研究与交付阻断插入点，禁止写产品代码 | `runs/execution/ci-r2-capability-execution-gate-20260905/worker_01.md` |
| `worker_02` | 审查 capability matrix 原子持久化、软链接与重放安全边界，禁止写产品代码 | `runs/execution/ci-r2-capability-execution-gate-20260905/worker_02.md` |
| `worker_03` | 设计最小负向与恢复测试矩阵，核查 CLI/宿主语义一致性，禁止写产品代码 | `runs/execution/ci-r2-capability-execution-gate-20260905/worker_03.md` |

## Manager

No execution manager is dispatched for this route; Codex reviews the worker outputs directly.

## Codex Acceptance

Codex 接受本切片的能力矩阵持久化、选择性执行门和恢复合同。未接受真实来源、
视觉门户、三宿主实跑或发布完成；详见同名 review、metrics 和 Task checkpoint。
