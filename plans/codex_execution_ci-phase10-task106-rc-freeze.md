# Codex Execution Plan: ci-phase10-task106-rc-freeze

Objective: Task 10.6A：在不触碰真实旧根、不创建 RC commit 的前提下，审计并补齐 clean-commit bundle provenance、最终 fresh-install 内容合同、recovery-package-v1 生产者/严格回执及恢复演练测试，为后续 source closure 和最终 RC 重跑建立失败关闭基础。

## Work Items

| Worker | Assigned item | Report |
|---|---|---|
| `worker_01` | 审计 tools/build_bundle.py、verify_bundle.py、bundle_contract.py、package manifest 和 fresh-install tests，提出 clean commit provenance、dirty fail-closed、最终内容闭合的最小实现与精确测试。 | `runs/execution/ci-phase10-task106-rc-freeze/worker_01.md` |
| `worker_02` | 审计 Task 10.5 recovery consumer 合同与现有恢复能力，设计 recovery-package-v1 manifest/receipt schema、stdlib-first 构建器、隔离恢复演练和负向测试；不得读取真实旧根。 | `runs/execution/ci-phase10-task106-rc-freeze/worker_02.md` |
| `worker_03` | 审计 full-matrix/required-v12/host receipts/final freeze 的当前实现边界，给出 10.6A 必须补齐的 owner-stage/旧证据拒绝/RC digest 绑定测试与后续 10.6C-D 可执行交接。 | `runs/execution/ci-phase10-task106-rc-freeze/worker_03.md` |

## Manager

No execution manager is dispatched for this route; Codex reviews the worker outputs directly.

## Codex Acceptance

- Re-read all worker-touched bytes and integrate the smallest coherent contracts; worker 03 remains advisory.
- Require tmp-only tests, exact source/RC/package digest bindings, unknown-field rejection, dirty/source mismatch failure, and no real-root access.
- Run focused tests, package/bundle/fresh-install adjacent regression, Ruff and mypy before accepting 10.6A.
- Do not create an RC commit, write the external acceptance root, invoke real hosts, or claim visual/scientific/final acceptance in this execution packet.
