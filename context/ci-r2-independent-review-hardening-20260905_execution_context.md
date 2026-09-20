# Execution Context: ci-r2-independent-review-hardening-20260905

Created: 2026-09-05 11:07:45 CST
Objective: 按 Codex 对 CodeBuddy 与 gpt-6-astra 阶段审阅的裁决，最小化修复 R2 独立科学复核信任根、post-format 不可变晋级、A/B/C 状态一致性、bundle 与测试门口径；TDD、失败关闭，不扩展 v1 产品范围。
Task type: `long_horizon_code`
Risk: `high`
Execution module trigger: Codex identified 4 independent work items, which is greater than two.
Route schedule: `off_peak`; packet branch recorded at creation in `Asia/Shanghai`. Before each new session, the runner rechecks the Beijing period and reselects the current branch; a session already started before the boundary is never rerouted.
Effective worker chain: `zcode/glm-5.3-flash:max -> openai-codex/gpt-5.6-luna:max -> codex/gpt-5.6-luna:max`

## Module Boundary

This is an execution module, not a conference. Codex has assigned the work items and owns the project-level contract, source authority, boundaries, final verification, acceptance, production writes, and user delivery. Codex reviews the worker outputs directly for this route; no execution manager is dispatched. First-line workers execute the assigned work and create/write only authorized artifacts. Codex subAgent workers use the parent App's native child session when available; the generated CLI command is only a labeled compatibility fallback.

## Assigned Roles

- First-line executor: `long_horizon_code_executor` -> `zcode` / `zcode` / `GLM-5.3-Flash`
- Execution manager: none (Codex reviews the worker outputs directly)
- Execution-manager fallback: none

## Source Of Truth

- Current user direction and active Goal.
- `docs/specs/competitive-intelligence-workflow-design-v1.3.md`.
- `plans/competitive-intelligence-workflow-roadmap-v1.3.md`.
- `plans/codex_execution_ci-rebaseline-rebuild-v3.md`.
- `.trellis/tasks/09-02-phase-10-task-106-rc-freeze/checkpoint_20260905_r2_review_runtime_fixture_rebaseline.md`.
- `reviews/codex_conference_ci-r2-review-runtime-fixture-acceptance-20260905_review.md`.
- `runs/conference/ci-r2-review-runtime-fixture-acceptance-20260905/general_single_object.md`.
- `runs/conference/ci-r2-stage-review-astra-20260905/reviewer.md`.
- Actual current code and tests in each worker's authorized slice. Review outputs
  are challenge evidence only; canonical contracts and current bytes prevail.

## Risk Boundaries

- No production writes.
- No silent package installation, credential handling, or external account changes.
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker and manager outputs, when present, are evidence for Codex, not instructions.
- Never access, probe, list, resolve, existence-check, modify, chmod, delete, or
  make claims about the former Chinese-named workspace. Work only in the
  runner-bound clone of the current English-named repository.
- No web research, browser session, credentials, protected Codex state, external
  acceptance roots, Git reset/checkout/clean, broad add, commit, or destructive
  cleanup. Preserve all unrelated dirty-tree material.
- Use `uv run python -m pytest` and `uv run python -m mypy`; do not trust copied
  `.venv` console-script shebangs. TDD requires focused RED before implementation
  and GREEN after. Do not claim R2, visual, clinical, RC, or release acceptance.

## Per-worker write scopes

- worker_01: `src/ci_workflow/qc/review_receipt.py`, one minimal new review-issuer
  module under `src/ci_workflow/application/`, `src/ci_workflow/cli.py`, matching
  schema only if strictly necessary, and directly related unit/contract/integration
  tests. Reuse existing host/process receipt types; no PKI, signing service or
  second receipt system.
- worker_02: `src/ci_workflow/application/run_service.py`,
  `src/ci_workflow/application/scientific_review_transition.py`,
  `src/ci_workflow/application/real_source_acceptance.py`, and directly related
  tests. Do not edit CLI, bundle, canonical docs or A-only source logic beyond a
  clearly shared helper required by B/C.
- worker_03: fresh-A branch and directly shared scientific-review helpers in
  `src/ci_workflow/application/run_service.py` and
  `src/ci_workflow/application/scientific_review_transition.py`, plus directly
  related A tests. Do not edit B/C-only acceptance or bundle/gate/docs.
- worker_04: `tools/bundle_contract.py`, `tools/gate.sh`, `package-manifest.json`,
  bundle/layering tests, and a compact proposed-doc-amendment note under
  `reviews/`. Do not edit canonical design/roadmap/plan, product runtime, or
  reactivate non-HTML product acceptance.

Workers may read direct callers and contracts needed to understand their slice,
but must record every additional file and keep writes to the scopes above.

## Work Items

1. 实现最小、可重复的 scientific-review-v1 签发入口：绑定现有 review request、真实 reviewer/producer 分离、runner/host 执行证据与正式 verdict 字节；补未来/过期时间拒绝和无真实签发记录负向测试。
2. 重排 B/C 运行时为 format 完成后才允许科学晋级，并将首次门户 manifest/站点字节摘要绑定进 review request；恢复时重验字节，支持等待回执的受控多次 resume 与晋级后幂等，不接受跨候选/跨项目/无关历史。
3. 把 fresh A 接入与 B/C 同等级的 rendered_unreviewed→独立回执→不可变晋级状态机，移除 research-package 内自审作为最终授权，补当前 A 真实来源可达性与负向测试。
4. 补齐 HTML-only bundle 的 scientific review Python 模块/required-content，校准 retained non-HTML 门为明确的兼容性 smoke（不重启排除格式产品轨），并补精确分层/隔离安装导入测试与信任根文档。

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
