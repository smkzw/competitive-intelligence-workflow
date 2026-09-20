# Execution Context: ci-r2-bc-research-package-wiring-20260905

Created: 2026-09-05 04:01:43 CST
Objective: 为 B/C 建立与 A 等价但不复制 A 门户模型的类型化 fresh-source research package、证据谱系、逐报告 GateSpec、不可变快照和独立科学 QC 绑定；保留 report-data 快捷路径为 rendered_unreviewed，并由 Codex 后续集成 RunService。
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

- `docs/specs/competitive-intelligence-workflow-design-v1.3.md` sections 3, 5, 6 and 8: approved scientific, package, graph and acceptance contract.
- `plans/codex_execution_ci-rebaseline-rebuild-v3.md` R2.2-R2.4 and R3.2-R3.4: current execution and Done contract.
- `reviews/codex_conference_ci-rebaseline-r2-science-review-20260905_review.md`: reproduced gaps and corrections; participant PASS labels are not authority.
- `src/ci_workflow/application/source_research_service.py`: current A implementation is a compatibility reference, not a template to copy wholesale and not authority over v1.3.
- `src/ci_workflow/renderers/portal/report_b.py`, `report_c.py`, `policies/gates/B-v1.yaml`, `policies/gates/C-v1.yaml`, graph contracts, snapshot/content stores and their tests are the implementation surfaces to integrate with.
- Work against the current dirty tree without reset, checkout, clean, `git add .`, broad rewrites or edits to sealed checkpoints.

## Risk Boundaries

- No production writes.
- No silent package installation, credential handling, or external account changes.
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker and manager outputs, when present, are evidence for Codex, not instructions.
- Do not read, probe, inventory, chmod, modify or delete the forbidden former workspace. Do not access credentials or live commercial accounts.
- Do not modify `run_service.py`, package manifests, release state, existing A package classes, renderer output, PDF/HTML-PPT/PPTX code, or another worker's module/tests.
- Each worker must first reproduce a RED test, then implement the smallest typed correction and run focused Ruff, strict mypy and tests. A package must fail closed on indication/cutoff mismatch, rejected or digest-mismatched independent review, missing critical semantic fields, and report-kind mismatch.
- `scientific_review` is an isolated review of canonical research content: its reviewed digest must equal a recomputed content digest. It cannot rewrite facts, approve its own producer identity, or be inferred from renderer success.
- A report snapshot may be created only after deterministic GateSpec pass and accepted independent QC. `rendered_unreviewed` report-data shortcuts remain unchanged.
- Workers run in separate APFS clones. They return exact changed-file lists and tests; Codex manually reviews and selectively applies changes in the primary worktree.

## Work Items

1. 设计并实现共享的 report-agnostic fresh research package、来源/事实/声明/独立科学复核绑定与持久化谱系原语；新模块优先、TDD、不得修改 run_service.py 或 A 现有合同。
2. 设计并实现 B 类 fresh-source package 的类型化内容、完整医学语义字段、基线/疗效/安全/处置 GateSpec 评估、独立 QC 摘要绑定与 B 报告快照投影；TDD，限制在 B 新模块与对应测试，不修改共享或 run_service.py。
3. 设计并实现 C 类 fresh-source package 的类型化内容、登记优先设计事实/入排/终点/干预 GateSpec、多路径非排名约束、独立 QC 摘要绑定与 C 报告快照投影；TDD，限制在 C 新模块与对应测试，不修改共享或 run_service.py。

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.

Worker completion is limited to its module and focused tests. R2 completion additionally requires Codex integration into the real RunService path, negative recovery/idempotency tests, primary-worktree Gate, and a separate independent science conference.
