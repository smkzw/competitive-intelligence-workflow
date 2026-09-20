# Codex Execution Plan: ci-phase9-task95-candidate-bundle

Objective: 依据已批准 Task 9.5 构建完整 .tar.zst 竞品调研 Skill bundle，完成内容寻址校验、隔离 fresh-install、Codex/Hermes/OMP 三真实入口回执及中文安装说明；首版实际输出仅站点式 HTML，不覆盖旧入口，不把源码 checkout 或同进程适配器 JSON 冒充最终包验收。

## Work Items

| Worker | Assigned item | Report |
|---|---|---|
| `worker_01` | 实现 PK01–PK02：最小 allowlist bundle 构建器、逐文件 manifest、外部 SHA-256、校验器及缺失/额外/摘要漂移/路径异常反例；不得打包缓存、旧输出或凭据。 | `runs/execution/ci-phase9-task95-candidate-bundle/worker_01.md` |
| `worker_02` | 实现 PK03–PK04：隔离 fresh-install 布局与真实宿主外部进程 runner，复用 Task 9.4 唯一 HostReceipt；不得同进程伪造三份，不覆盖旧入口。 | `runs/execution/ci-phase9-task95-candidate-bundle/worker_02.md` |
| `worker_03` | 实现 PK05–PK06：fresh-install/conformance/real-host 测试、中文安装说明与验收归档合同；首版仅 HTML，用户提示必须中文原生且区分技术故障与证据不足。 | `runs/execution/ci-phase9-task95-candidate-bundle/worker_03.md` |

## Manager

No execution manager is dispatched for this route; Codex reviews the worker outputs directly.

## Codex Acceptance

Accepted after bundle/package verification, canonical fresh-install, three PATH-resolved host runs, focused tests, same-session independent conference re-review, and current archive binding. See `reviews/codex_execution_ci-phase9-task95-candidate-bundle_review.md`.
