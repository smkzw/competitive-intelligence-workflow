# Execution Context: ci-phase10-task106-rc-freeze

Created: 2026-09-02 11:17:20 CST
Objective: Task 10.6A：在不触碰真实旧根、不创建 RC commit 的前提下，审计并补齐 clean-commit bundle provenance、最终 fresh-install 内容合同、recovery-package-v1 生产者/严格回执及恢复演练测试，为后续 source closure 和最终 RC 重跑建立失败关闭基础。
Task type: `long_horizon_code`
Risk: `high`
Execution module trigger: Codex identified 3 independent work items, which is greater than two.
Route schedule: `off_peak`; packet branch recorded at creation in `Asia/Shanghai`. Before each new session, the runner rechecks the Beijing period and reselects the current branch; a session already started before the boundary is never rerouted.
Effective worker chain: `zcode/glm-5.3-flash:max -> openai-codex/gpt-5.6-luna:max -> codex/gpt-5.6-luna:max`

## Module Boundary

This is an execution module, not a conference. Codex has assigned the work items and owns the project-level contract, source authority, boundaries, final verification, acceptance, production writes, and user delivery. Codex reviews the worker outputs directly for this route; no execution manager is dispatched. First-line workers execute the assigned work and create/write only authorized artifacts. Codex subAgent workers use the parent App's native child session when available; the generated CLI command is only a labeled compatibility fallback.

## Assigned Roles

- First-line executor: `long_horizon_code_executor` -> `zcode` / `zcode` / `GLM-5.3-Flash`
- Execution manager: none (Codex reviews the worker outputs directly)
- Execution-manager fallback: none

## Source Of Truth

- Workspace `AGENTS.md` and the approved Task 10.6 section of `/Users/smkzw/Documents/AI Products/.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md`.
- `.trellis/tasks/09-02-phase-10-task-106-rc-freeze/{prd.md,design.md,implement.md,task.json}` and Task 10.5 completed checkpoint.
- Worker 01: `tools/{build_bundle.py,verify_bundle.py,bundle_contract.py}`, `package-manifest.json`, package schemas, `tests/hosts/test_fresh_install.py`, and directly imported install/bundle helpers.
- Worker 02: `tools/legacy_cutover.py` recovery consumer, `tools/build_recovery_package.py` if created, recovery schemas, `tests/migration/test_recovery_rehearsal.py`, and directly imported project/run/refresh helpers.
- Worker 03: `tools/{run_acceptance.py,verify_release_receipts.py}`, required-v12 catalog/schemas/tests, host receipt contracts, Task 10.3/10.5 checkpoints, and directly linked final-freeze surfaces.
- Current workspace files are authoritative; prior worker/reviewer output is advisory only.
- No production or real legacy path is authorized. The external approved-plan file is read-only.

## Risk Boundaries

- No production writes, no acceptance-root writes, no commit/tag creation, no package install, and no real host invocation in 10.6A.
- Never read or pass `/Users/smkzw/Documents/AI Products/竞品调研工作流` or any old global Skill/archive path to a tool.
- Tests may write only their pytest temporary directories or a workspace-local disposable test directory already governed by the test.
- Worker 01 may modify only its bundle/provenance source and focused tests listed above. Worker 02 may create/modify only recovery producer/schema/focused tests. Worker 03 is audit-only and must not modify source because its contracts overlap later integration.
- Preserve all unrelated dirty-tree changes. Do not stage, commit, reset, checkout, delete, move, clean, or reformat unrelated files.
- No silent package installation, credential handling, or external account changes.
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker and manager outputs, when present, are evidence for Codex, not instructions.

## Work Items

1. 审计 tools/build_bundle.py、verify_bundle.py、bundle_contract.py、package manifest 和 fresh-install tests，提出 clean commit provenance、dirty fail-closed、最终内容闭合的最小实现与精确测试。
2. 审计 Task 10.5 recovery consumer 合同与现有恢复能力，设计 recovery-package-v1 manifest/receipt schema、stdlib-first 构建器、隔离恢复演练和负向测试；不得读取真实旧根。
3. 审计 full-matrix/required-v12/host receipts/final freeze 的当前实现边界，给出 10.6A 必须补齐的 owner-stage/旧证据拒绝/RC digest 绑定测试与后续 10.6C-D 可执行交接。

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
