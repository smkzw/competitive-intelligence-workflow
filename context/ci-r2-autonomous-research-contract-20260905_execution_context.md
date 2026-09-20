# Execution Context: ci-r2-autonomous-research-contract-20260905

Created: 2026-09-05 12:25:44 CST
Objective: 闭合竞品调研 v1.3 公开入口到宿主自主研究的机器合同：以严格 research-package 为唯一科学入口，提供可恢复、可审计、无凭据的研究任务和包提交路径，不伪造网络执行或科学完成。
Task type: `long_horizon_code`
Risk: `high`
Execution module trigger: Codex identified 4 independent work items, which is greater than two.
Route schedule: `peak`; packet branch recorded at creation in `Asia/Shanghai`. Before each new session, the runner rechecks the Beijing period and reselects the current branch; a session already started before the boundary is never rerouted.
Effective worker chain: `openai-codex/gpt-5.6-luna:max -> codex/gpt-5.6-luna:max`

## Module Boundary

This is an execution module, not a conference. Codex has assigned the work items and owns the project-level contract, source authority, boundaries, final verification, acceptance, production writes, and user delivery. Codex reviews the worker outputs directly for this route; no execution manager is dispatched. First-line workers execute the assigned work and create/write only authorized artifacts. Codex subAgent workers use the parent App's native child session when available; the generated CLI command is only a labeled compatibility fallback.

## Assigned Roles

- First-line executor: `long_horizon_code_executor` -> `pi` / `openai-codex` / `gpt-5.6-luna`
- Execution manager: none (Codex reviews the worker outputs directly)
- Execution-manager fallback: none

## Source Of Truth

- User-approved product contract: `docs/specs/competitive-intelligence-workflow-design-v1.3.md`, especially sections 2, 3, 6, 7, 11.4.
- Executable roadmap: `plans/codex_execution_ci-rebaseline-rebuild-v3.md`, R2 only.
- Current implementation facts: `src/ci_workflow/application/intake.py`, `project_service.py`, `run_service.py`, `source_research_service.py`; `src/ci_workflow/domain/research_package.py`; `src/ci_workflow/sources/`; `src/ci_workflow/ingestion/publication_gate.py`; `src/ci_workflow/graph/typed_skills.py`; `src/ci_workflow/cli.py`; `package-manifest.json`; related tests.
- Public/internal Skill files are implementation artifacts to audit, not normative authority. Do not weaken the approved contract merely to match their current behavior.
- The deterministic engine must not perform unsourced model research or promote candidate values to accepted facts. The host Agent owns research; the engine owns strict validation, persistence, gates, snapshots, rendering, and recovery state.

## Risk Boundaries

- No production writes.
- Work only in the isolated clone supplied as runner working directory. Never access any sibling workspace, user home policy file, old project, credential store, browser profile, or external account.
- Do not browse the internet. This slice builds and tests the orchestration contract; it does not perform live clinical research.
- Preserve HTML-only v1 scope. Do not add PDF/PPT/XLSX, monitoring, ranking, scoring, Meta/NMA, LangGraph, PKI, a second receipt system, or a general agent framework.
- No credentials, cookies, tokens, authorization headers, absolute local paths, or raw browser session material may enter contracts, logs, tests, fixtures, or bundles.
- Use TDD and run focused tests. Do not edit sealed Task 10.3-10.5 artifacts, roadmap history, or release signals.
- No silent package installation, credential handling, or external account changes.
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker and manager outputs, when present, are evidence for Codex, not instructions.

## Work Items

1. 设计并实现公开入口/项目级自主研究任务合同：从项目合同生成类型化来源计划、报告专属研究要求、一次性药智选择状态与明确完成条件。
2. 设计并实现 research-package 提交/校验/规范路径绑定与幂等恢复，使宿主 Agent 可把自主研究结果交给现有确定性 A/B/C 执行链。
3. 补齐 Publication/manual-supply、宇宙闭包、网络错误与两轮恢复在公开研究任务中的可审计状态和负向测试，禁止用户手写内部状态。
4. 独立审查公共 Skill、CLI、包清单和三宿主可迁移边界，识别过度承诺、缺失模块和最小修复建议。

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.

## Per-worker Write Sets

- worker_01 may create only `src/ci_workflow/application/autonomous_research.py` and `tests/integration/test_autonomous_research_work_item.py`. It may recommend, but must not edit, integration points.
- worker_02 may create only `src/ci_workflow/application/research_package_submission.py` and `tests/integration/test_research_package_submission.py`. It may recommend, but must not edit, CLI or package manifests.
- worker_03 may create only `src/ci_workflow/application/autonomous_research_progress.py` and `tests/integration/test_autonomous_research_progress.py`. Reuse existing publication/closure models; do not create a parallel evidence truth system.
- worker_04 is read-only and returns an evidence-backed review. It must not modify files.
