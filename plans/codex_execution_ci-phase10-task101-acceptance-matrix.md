# Codex Execution Plan: ci-phase10-task101-acceptance-matrix

Objective: 依据 Task 10.1 Trellis 合同和 ADR 0013，固定首版站点式 HTML 的正负基准矩阵：建立机器可读 acceptance catalog、full-matrix-v1、required-v12 脱敏场景、确定性失败关闭测试和中文矩阵说明，不实现或要求 PDF/PPT。

## Work Items

| Worker | Assigned item | Report |
|---|---|---|
| `worker_01` | 实现 M01–M03：acceptance catalog Schema、稳定 digest、full-matrix-v1 HTML-only 脱敏输入包与历史 cutoff 场景；先写反例 RED 后 GREEN。 | `runs/execution/ci-phase10-task101-acceptance-matrix/worker_01.md` |
| `worker_02` | 实现 M04：required-v12 18 个 case 族的内容寻址目录与 owner/scope/receipt/verifier/预期不变量；按 ADR 0013 收窄三项四格式语义。 | `runs/execution/ci-phase10-task101-acceptance-matrix/worker_02.md` |
| `worker_03` | 实现 M05–M06：test_fixture_catalog.py 双向闭合和负例测试、docs/acceptance/matrix.md 中文医学/验收人员说明，并复核与现有 fixtures/package 合同的相邻影响。 | `runs/execution/ci-phase10-task101-acceptance-matrix/worker_03.md` |

## Manager

No execution manager is dispatched for this route; Codex reviews the worker outputs directly.

## Codex Acceptance

TODO: verify artifacts, tests, source claims, rendered surfaces, blockers, and user-facing completeness.
