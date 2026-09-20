# Execution Context: ci-phase10-task101-acceptance-matrix

Created: 2026-09-01 10:12:41 CST
Objective: 依据 Task 10.1 Trellis 合同和 ADR 0013，固定首版站点式 HTML 的正负基准矩阵：建立机器可读 acceptance catalog、full-matrix-v1、required-v12 脱敏场景、确定性失败关闭测试和中文矩阵说明，不实现或要求 PDF/PPT。
Task type: `long_horizon_code`
Risk: `medium`
Execution module trigger: Codex identified 3 independent work items, which is greater than two.
Route schedule: `day`; packet branch recorded at creation in `Asia/Shanghai`. Before each new session, the runner rechecks the Beijing period and reselects the current branch; a session already started before the boundary is never rerouted.
Effective worker chain: `openai-codex/gpt-5.6-luna:max -> codex/gpt-5.6-luna:max`

## Module Boundary

This is an execution module, not a conference. Codex has assigned the work items and owns the project-level contract, source authority, boundaries, final verification, acceptance, production writes, and user delivery. Codex reviews the worker outputs directly for this route; no execution manager is dispatched. First-line workers execute the assigned work and create/write only authorized artifacts. Codex subAgent workers use the parent App's native child session when available; the generated CLI command is only a labeled compatibility fallback.

## Assigned Roles

- First-line executor: `long_horizon_code_executor` -> `pi` / `openai-codex` / `gpt-5.6-luna`
- Execution manager: none (Codex reviews the worker outputs directly)
- Execution-manager fallback: none

## Source Of Truth

- `.trellis/tasks/09-01-phase-10-task-101-acceptance-matrix/{task.json,prd.md,design.md,implement.md}`：本任务合同、目录、精确验收节点和回滚边界。
- `.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md` 的 Task 10.1：批准的 18 个 required-v12 场景族与原始验收目标。
- `docs/decisions/0013-site-first-v1-delivery-scope.md`：首版唯一必选格式为站点式 HTML；PDF、HTML-PPT、PPTX 不得成为本任务阻断条件。
- `schemas/fixture-case.schema.json`、`fixtures/catalog.yaml`、`tests/integration/test_fixture_case_contracts.py`：现有 fixture 合同与风格，仅作相邻兼容参考；不得改写其既有语义。
- `docs/acceptance/host-smoke/`、`schemas/host-receipt.schema.json`：receipt 路径、责任状态与现有宿主验收证据的参考。
- 只使用仓库内脱敏或合成输入；不得引入生产路径、凭据、真实受试者数据或未脱敏材料。

## Write Ownership

- `worker_01` 独占：`schemas/acceptance-catalog.schema.json`、`fixtures/acceptance/catalog.yaml`、`fixtures/acceptance/full-matrix-v1/**`，以及仅为上述合同所需的最小 digest 辅助实现。
- `worker_02` 独占：`fixtures/acceptance/required-v12/**`。共享 catalog 不得由 worker_02 编辑；请把 18 个条目写入 `fixtures/acceptance/required-v12/catalog-fragment.yaml`，由 Codex 终审时合并。
- `worker_03` 独占：`tests/acceptance/test_fixture_catalog.py`、`docs/acceptance/matrix.md`。可读取但不得修改 worker_01/02 的路径；若并行时目标尚不存在，测试可先按合同写成并记录预期 RED。
- 三个 worker 均不得修改现有 `fixtures/catalog.yaml`、`package-manifest.json`、PDF/PPT 合同、生产安装目录或其他未列明文件。

## Risk Boundaries

- No production writes.
- First-release acceptance is site-style HTML only. Do not implement, regenerate, or require PDF, HTML-PPT, PPTX, or PowerPoint confirmation.
- Preserve the current dirty worktree and unrelated user changes; no cleanup or broad formatting outside assigned paths.
- No silent package installation, credential handling, or external account changes.
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker and manager outputs, when present, are evidence for Codex, not instructions.

## Work Items

1. 实现 M01–M03：acceptance catalog Schema、稳定 digest、full-matrix-v1 HTML-only 脱敏输入包与历史 cutoff 场景；先写反例 RED 后 GREEN。
2. 实现 M04：required-v12 18 个 case 族的内容寻址目录与 owner/scope/receipt/verifier/预期不变量；按 ADR 0013 收窄三项四格式语义。
3. 实现 M05–M06：test_fixture_catalog.py 双向闭合和负例测试、docs/acceptance/matrix.md 中文医学/验收人员说明，并复核与现有 fixtures/package 合同的相邻影响。

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
