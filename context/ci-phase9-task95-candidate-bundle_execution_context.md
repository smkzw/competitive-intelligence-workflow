# Execution Context: ci-phase9-task95-candidate-bundle

Created: 2026-09-01 08:30:12 CST
Objective: 依据已批准 Task 9.5 构建完整 .tar.zst 竞品调研 Skill bundle，完成内容寻址校验、隔离 fresh-install、Codex/Hermes/OMP 三真实入口回执及中文安装说明；首版实际输出仅站点式 HTML，不覆盖旧入口，不把源码 checkout 或同进程适配器 JSON 冒充最终包验收。
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

- `.trellis/tasks/09-01-phase-9-task-95-candidate-bundle/{prd,design,implement}.md`
- `/Users/smkzw/Documents/AI Products/.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md` Task 9.5
- `.trellis/tasks/09-01-phase-9-task-94-host-adapters/checkpoint.md`
- `src/ci_workflow/application/host_smoke.py`, `src/ci_workflow/hosts/receipt.py`, `schemas/host-receipt.schema.json`
- `package-manifest.json`, `fixtures/catalog.yaml`, `fixtures/synthetic/host-smoke-v1/`
- `docs/decisions/0013-site-first-v1-delivery-scope.md`
- `contracts/kangzhe/design_specs/`（项目内化 site 设计合同，不回写通用 skill）
- 不添加生产路径，不覆盖旧入口；安装和真实宿主验证必须使用隔离候选根。

## Risk Boundaries

- No production writes.
- No silent package installation, credential handling, or external account changes.
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker and manager outputs, when present, are evidence for Codex, not instructions.

## Work Items

1. 实现 PK01–PK02：最小 allowlist bundle 构建器、逐文件 manifest、外部 SHA-256、校验器及缺失/额外/摘要漂移/路径异常反例；不得打包缓存、旧输出或凭据。
2. 实现 PK03–PK04：隔离 fresh-install 布局与真实宿主外部进程 runner，复用 Task 9.4 唯一 HostReceipt；不得同进程伪造三份，不覆盖旧入口。
3. 实现 PK05–PK06：fresh-install/conformance/real-host 测试、中文安装说明与验收归档合同；首版仅 HTML，用户提示必须中文原生且区分技术故障与证据不足。

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
