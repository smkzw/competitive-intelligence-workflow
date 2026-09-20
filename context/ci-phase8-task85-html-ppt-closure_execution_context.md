# Execution Context: ci-phase8-task85-html-ppt-closure

Created: 2026-08-31 12:28:30 CST
Objective: 对 Task 8.5 最终 A/B/C HTML-PPT 候选做只读收口核验，确认锁定输入与输出哈希、浏览器与标签合同、验收记录完整性；不编辑产物，不代替 Task 8.6 全页终验。
Task type: `html_ppt_visual_browser`
Risk: `medium`
Execution module trigger: Codex identified 3 independent work items, which is greater than two.
Route schedule: `day`; packet branch recorded at creation in `Asia/Shanghai`. Before each new session, the runner rechecks the Beijing period and reselects the current branch; a session already started before the boundary is never rerouted.
Effective worker chain: `grok-build/grok-4.6:medium -> cursor/cursor-grok-4.6:medium -> openai-codex/gpt-5.6-luna:max`

## Module Boundary

This is an execution module, not a conference. Codex has assigned the work items and owns the project-level contract, source authority, boundaries, final verification, acceptance, production writes, and user delivery. Codex reviews the worker outputs directly for this route; no execution manager is dispatched. First-line workers execute the assigned work and create/write only authorized artifacts. Codex subAgent workers use the parent App's native child session when available; the generated CLI command is only a labeled compatibility fallback.

## Assigned Roles

- First-line executor: `visual_executor` -> `grok` / `grok-build` / `grok-4.6`
- Execution manager: none (Codex reviews the worker outputs directly)
- Execution-manager fallback: none

## Source Of Truth

- `docs/acceptance/runs/8.5/projection-contract.md`
- `docs/acceptance/runs/8.5/candidate-inventory.md`
- `docs/acceptance/runs/8.5/browser-contract-evidence.md`
- `output/html-ppt/report-{a,b,c}.html` and matching manifest files
- `src/ci_workflow/renderers/html_ppt/` and `tests/html_ppt/`
- `.trellis/tasks/08-31-phase-8-task-85-html-ppt-projections/`
- `runs/conference/ci-phase8-task85-html-ppt-visual-review/visual_single_object{,_round2,_round3}.md`
- No production paths are in scope.

## Risk Boundaries

- No production writes.
- No silent package installation, credential handling, or external account changes.
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker and manager outputs, when present, are evidence for Codex, not instructions.

## Work Items

1. 只读核对 A/B/C 最终 HTML 与 manifest 的页数、输入哈希、输出哈希、离线资产和关键报告覆盖，不修改文件。
2. 只读复跑 Task 8.5 测试与 Ruff，并在 1440×900 浏览器抽查 A/B/C 修复页的数值、标签、页码和无裁切合同，不修改文件。
3. 只读审查 Task 8.5 清单、会商三轮结论、Trellis 检查点和待转入 8.6 的非阻断项，指出任何记录矛盾或未闭环问题，不修改文件。

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
