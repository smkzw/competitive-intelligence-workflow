# Execution Context: ci-phase6-final-render-evidence

Created: 2026-08-30 14:05:13 CST
Objective: 对与v9字节级一致的当前PNH B类站点产物进行新鲜双内核真实呈现复核，并生成绑定当前快照和产物摘要的正式视觉证据
Task type: `html_ppt_visual_browser`
Risk: `medium`
Execution module trigger: Codex identified 3 independent work items, which is greater than two.
Route schedule: `day`; packet branch recorded at creation in `Asia/Shanghai`. Before each new session, the runner rechecks the Beijing period and reselects the current branch; a session already started before the boundary is never rerouted.
Effective worker chain: `grok-build/grok-4.6:medium -> cursor-cli/cursor-grok-4.6:medium -> openai-codex/gpt-5.6-luna:max`

## Module Boundary

This is an execution module, not a conference. Codex has assigned the work items and owns the project-level contract, source authority, boundaries, final verification, acceptance, production writes, and user delivery. Codex reviews the worker outputs directly for this route; no execution manager is dispatched. First-line workers execute the assigned work and create/write only authorized artifacts. Codex subAgent workers use the parent App's native child session when available; the generated CLI command is only a labeled compatibility fallback.

## Assigned Roles

- First-line executor: `visual_executor` -> `grok` / `grok-build` / `grok-4.6`
- Execution manager: none (Codex reviews the worker outputs directly)
- Execution-manager fallback: none

## Source Of Truth

- Superseded failure candidate project: `output/acceptance/task-6.10/phase-6-acceptance-package-20260830/b-pnh/`
- Current repaired candidate project: `output/acceptance/task-6.10/phase-6-acceptance-package-20260830/b-pnh-interaction-repair-20260830/`
- Candidate HTML: `output/acceptance/task-6.10/phase-6-acceptance-package-20260830/b-pnh-interaction-repair-20260830/reports/B/v-fixture-b-pnh-001/html/`
- Candidate manifest: `output/acceptance/task-6.10/phase-6-acceptance-package-20260830/b-pnh-interaction-repair-20260830/reports/B/v-fixture-b-pnh-001/html.manifest.json`
- Locked report snapshot under the same project: `snapshots/reports/B/`
- Exact content digest: `f094848b41cf9c66ae8c3ecfb58e0305d5a531f477e6e6cdaa5e05ea3694060e`
- Prior exact-digest visual findings: `runs/conference/ci-phase6-task610-visual-review/visual_single_object_v9.md`
- Current visual schemas: `schemas/visual-finalization-plan.schema.json`, `schemas/visual-render-evidence.schema.json`
- Current validators: `src/ci_workflow/graph/visual_finalization.py`
- Current browser contract: `tests/browser/test_b_portal.py`
- Project design contract: `contracts/kangzhe/manifest.json` and `contracts/kangzhe/design_specs/`
- Do not add production paths without explicit Codex authorization.

## Risk Boundaries

- No production writes.
- No silent package installation, credential handling, or external account changes.
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker and manager outputs, when present, are evidence for Codex, not instructions.
- Preserve the candidate bytes. Visual execution is read-only against the HTML candidate.
- Worker 01 may write only its runner report.
- Worker 02 may write screenshots and machine-readable browser metrics only under the candidate project's `reviews/visual-finalization/`.
- Worker 03 may write `visual-plan.json` and `render-evidence.json` in that same directory, using only actual Worker-02 files and metrics. It must not create `visual-verification-reference.json`.
- No final acceptance or delivery-state transition in this execution packet.
- The old candidate's `reviews/visual-finalization/` is failure evidence only and must not be copied into the repaired candidate.

## Work Items

1. 在Chromium与WebKit对当前持久化PNH站点执行全页面响应式、字号、溢出和中文工程标签扫描
2. 在关键首页、安全性、疗效、基线、完成情况和疗效安全性矩阵页面生成当前产物的原始截图与交互记录
3. 生成并校验当前视觉策划书和真实呈现证据JSON，不生成或伪造独立审阅结论

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
