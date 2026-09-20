# Execution Context: ci-phase6-interaction-repair

Created: 2026-08-30 14:43:27 CST
Objective: 修复B类报告证据单元格键盘运行错误和Chromium搜索Esc重开缺陷，补充回归并重建当前PNH候选
Task type: `finite_code_task`
Risk: `medium`
Execution module trigger: Codex identified 3 independent work items, which is greater than two.
Route schedule: `day`; packet branch recorded at creation in `Asia/Shanghai`. Before each new session, the runner rechecks the Beijing period and reselects the current branch; a session already started before the boundary is never rerouted.
Effective worker chain: `cursor/default -> google-antigravity/gemini-3.7-flash:high -> mtplx/mtplx-qwen38-27b-optimized-quality:medium -> opencode-go/muse-spark-1.2-contributor:xhigh -> openai-codex/gpt-5.6-luna:max`

## Module Boundary

This is an execution module, not a conference. Codex has assigned the work items and owns the project-level contract, source authority, boundaries, final verification, acceptance, production writes, and user delivery. Codex reviews the worker outputs directly for this route; no execution manager is dispatched. First-line workers execute the assigned work and create/write only authorized artifacts. Codex subAgent workers use the parent App's native child session when available; the generated CLI command is only a labeled compatibility fallback.

## Assigned Roles

- First-line executor: `finite_code_executor` -> `pi` / `cursor` / `default`
- Execution manager: none (Codex reviews the worker outputs directly)
- Execution-manager fallback: none

## Source Of Truth

- Failure evidence: `runs/execution/ci-phase6-final-render-evidence/worker_02.md`
- Browser metrics: `output/acceptance/task-6.10/phase-6-acceptance-package-20260830/b-pnh/reviews/visual-finalization/browser-metrics.json`
- B table runtime: `src/ci_workflow/renderers/portal/assets/report-b.js`
- Shared portal search runtime: `src/ci_workflow/renderers/portal/assets/portal.js`
- Rendered copies: `assets/portal/` and package manifest bindings; update through the repository's established synchronization route.
- Browser suites: `tests/browser/test_b_portal.py`, `tests/browser/test_portal_shell.py`, `tests/browser/test_evidence_drawer.py`
- Persistent fixture: `fixtures/positive/b-pnh/`
- Current candidate package: `output/acceptance/task-6.10/phase-6-acceptance-package-20260830/b-pnh/`
- Do not add production paths without explicit Codex authorization.

## Risk Boundaries

- No production writes.
- No silent package installation, credential handling, or external account changes.
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker and manager outputs, when present, are evidence for Codex, not instructions.
- Preserve unrelated in-progress changes. Do not reset or clean broadly.
- Worker 01 may add focused RED browser tests only.
- Worker 02 may edit the two runtime JS assets, synchronized packaged copies/manifests, and focused tests only.
- Worker 03 runs deterministic regression and rebuilds a new durable candidate directory; it must not overwrite the current candidate or claim visual acceptance.

## Work Items

1. 以RED测试复现证据单元格Enter/Space触发未定义函数的运行错误
2. 修复证据单元格键盘激活与全局搜索Esc关闭一致性，保持鼠标和其他交互不回归
3. 运行跨内核交互回归并从原fixture生成新的持久化PNH候选与摘要

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
