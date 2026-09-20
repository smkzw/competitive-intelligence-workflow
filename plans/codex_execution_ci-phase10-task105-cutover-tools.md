# Codex Execution Plan: ci-phase10-task105-cutover-tools

Objective: 实现并冻结前验证 Task 10.5 精准切换工具与 required-v12 release receipt 闭环；代码和测试仅针对显式 registry 与临时 fixture 根，禁止对真实旧根执行 inventory/apply。

## Work Items

| Worker | Assigned item | Report |
|---|---|---|
| `worker_01` | 审计精准 inventory/validate/apply/absence-check 的最小失败关闭合同、路径与 inode/symlink 边界，给 Codex 实施建议；只读。 | `runs/execution/ci-phase10-task105-cutover-tools/worker_01.md` |
| `worker_02` | 审计 required-v12 catalog、现有 pre-RC receipt 语义及新 release-case receipt schema/owner-stage closure 所需最小字段与负例；只读。 | `runs/execution/ci-phase10-task105-cutover-tools/worker_02.md` |
| `worker_03` | 审计 Task 10.5 测试设计、tmp_path 隔离、恢复包门、授权摘要和幂等性风险，识别遗漏与相邻回归；只读。 | `runs/execution/ci-phase10-task105-cutover-tools/worker_03.md` |

## Manager

No execution manager is dispatched for this route; Codex reviews the worker outputs directly.

## Codex Acceptance

- Verify no default real path exists and all mutation tests prove `tmp_path` isolation.
- Verify exact path/root, no-symlink-follow, device/inode/type/digest drift, recovery receipt, authorization digest, idempotence, and residual detection.
- Verify receipt schema/digests bind catalog, package, RC, owner, run/session, input/artifact/verdict and time; pending is never accepted and only catalog-declared optional adapters may be `not_applicable` with project-contract binding.
- Run focused tests, Ruff, mypy, package-manifest tests, legacy scanner, and relevant acceptance regressions.
- Obtain independent conference review before final acceptance; no real cutover, RC freeze, Task 10.8 absence closure, or product acceptance in this task.
