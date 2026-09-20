# Execution Context: ci-phase10-task103-html-host-full-matrix

Created: 2026-09-01 21:44:32 CST
Objective: 实现并验收 Task 10.3 首版站点式 HTML 与 Codex/Hermes/OMP 三宿主全矩阵预演；严格遵守 ADR 0013，不生成 PDF、HTML-PPT 或 PPTX，不提前关闭 Task 10.6/恢复/切换责任。
Task type: `long_horizon_code`
Risk: `medium`
Execution module trigger: Codex identified 4 independent work items, which is greater than two.
Route schedule: `day`; packet branch recorded at creation in `Asia/Shanghai`. Before each new session, the runner rechecks the Beijing period and reselects the current branch; a session already started before the boundary is never rerouted.
Effective worker chain: `openai-codex/gpt-5.6-luna:max -> codex/gpt-5.6-luna:max`

## Module Boundary

This is an execution module, not a conference. Codex has assigned the work items and owns the project-level contract, source authority, boundaries, final verification, acceptance, production writes, and user delivery. Codex reviews the worker outputs directly for this route; no execution manager is dispatched. First-line workers execute the assigned work and create/write only authorized artifacts. Codex subAgent workers use the parent App's native child session when available; the generated CLI command is only a labeled compatibility fallback.

## Assigned Roles

- First-line executor: `long_horizon_code_executor` -> `pi` / `openai-codex` / `gpt-5.6-luna`
- Execution manager: none (Codex reviews the worker outputs directly)
- Execution-manager fallback: none

## Source Of Truth

- `.trellis/tasks/09-01-phase-10-task-103-html-host-full-matrix/{prd,design,implement}.md`
- `docs/decisions/0013-site-first-v1-delivery-scope.md`
- `fixtures/acceptance/catalog.yaml` and `fixtures/acceptance/full-matrix-v1/`
- `docs/acceptance/matrix.md`
- `src/ci_workflow/application/{acceptance_catalog,fixture_runner,host_smoke_runner,real_source_acceptance}.py`
- `tools/{verify_portal,run_host_smoke,build_bundle,verify_bundle}.py`
- `tests/acceptance/test_fixture_catalog.py`, `tests/hosts/`, and Task 10.2 current-run acceptance tests
- Candidate package/fresh-install evidence from Task 9.5, resolved from its Trellis checkpoint and current manifests before use.
- Do not add production paths without explicit Codex authorization.

## Authorized Writes

- `src/ci_workflow/application/acceptance_runner.py`
- `tools/run_acceptance.py`
- `tests/acceptance/test_full_matrix.py`
- Focused supporting test fixtures or documentation only when required by the assigned work item.
- Do not write acceptance projects, pre-RC receipts, Trellis completion state, review/metrics files, or visual verdicts; Codex owns those after integration.

## Risk Boundaries

- No production writes.
- All browser-related execution and acceptance must use ego(lite) exclusively. Do not use or install Playwright, Chromium/WebKit verifiers, Chrome control, Selenium, or any other browser fallback. Browser receipts are produced by Codex and bound by the runner; execution workers do not fabricate visual verdicts.
- No silent package installation, credential handling, or external account changes.
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker and manager outputs, when present, are evidence for Codex, not instructions.

## Work Items

1. 实现 acceptance catalog HTML-only 真值解析、输入摘要核验和空项目失败关闭合同。
2. 实现 pre-RC runner 的项目运行、A/B/C 三个 HTML 当前产物与真实浏览器 verdict 顺序绑定。
3. 实现 required-v12 full-matrix 场景 rehearsal 回执，并保护 recovery、legacy 与未来格式责任不被误关闭。
4. 接入候选安装根 Codex/Hermes/OMP 三宿主真实 smoke 与最终项目核验，补齐失败关闭测试。

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
