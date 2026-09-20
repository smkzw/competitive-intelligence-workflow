# Codex Execution Plan: ci-r2-yaozh-routing-20260905

Objective: 将项目级药智三态回答接入来源政策、自动研究工作项和宿主能力预检，保持辅助路线非阻断、会话失效可恢复且无凭据进入 artifact

## Work Items

| Worker | Assigned item | Report |
|---|---|---|
| `worker_01` | W01: 核查药智来源权威矩阵与自动研究任务三态合同，给出最小实现或补丁 | `runs/execution/ci-r2-yaozh-routing-20260905/worker_01.md` |
| `worker_02` | W02: 核查能力预检与 run service 的可选登录浏览器依赖，防止核心研究被错误阻断 | `runs/execution/ci-r2-yaozh-routing-20260905/worker_02.md` |
| `worker_03` | W03: 设计并验证负向测试、凭据边界、幂等与正式文档更新 | `runs/execution/ci-r2-yaozh-routing-20260905/worker_03.md` |

## Manager

No execution manager is dispatched for this route; Codex reviews the worker outputs directly.

## Codex Acceptance

Accepted as a bounded R2 contract slice after Codex reviewed all worker reports, incorporated
the applicable findings, reproduced RED cases, ran integration/full gate, and verified an
isolated 324-file HTML-only bundle. Real Yaozh browser access, core preflight execution gating,
three-host execution and R2 completion remain outside this slice.
