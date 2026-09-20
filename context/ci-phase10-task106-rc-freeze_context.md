# Task Context: ci-phase10-task106-rc-freeze

Created: 2026-09-02 11:16:16
Objective: Task 10.6：从最终源树建立可审计 clean-commit RC，重建并验证最终 bundle，fresh-install 后重跑 A/B/C 与 full-matrix，生成并演练 recovery-package-v1，独立完成科学/视觉/包/恢复验收并冻结 RC；真实旧根保持零触碰。
Task type: `long_horizon_code`
Risk: `high`
Selected agent route: `zcode` / `GLM-5.3-Flash` / `max`

## Trigger Reason

This task was initialized through the Codex x Hermes complex-task entrypoint because it is expected to involve more than three execution steps, research/writing/report/code/report-visual work, or source-grounded verification.

## Source Of Truth

- TODO: Add authoritative local files, extracts, datasets, screenshots, URLs, or user-provided materials.
- Do not add production paths unless the user has explicitly authorized reading them for this task.

## Scope

- In scope: TODO
- Out of scope: TODO

## Success Criteria

- TODO

## Risk Boundaries

- Do not write to production paths until Codex review gate passes and writable paths are explicit.
- The delegated agent is not final authority; Codex owns verification and acceptance.

## Timeout Policy

- Do not mark the delegated agent failed for slow response alone.
- For complex or artifact-heavy work, wait and poll generously; use conference mode when multiple independent model perspectives are needed.
- Failure requires terminal error, provider exhaustion/rate limit after controlled retry, empty/truncated retry output, or no progress after hard wait plus one retry.
- A provider catalog/auth/transport preflight is diagnostic, not a live capability verdict: timeout, auth refresh failure, malformed output, or a stale/incomplete catalog must be recorded and followed by one real route attempt. Explicit user-selected routes are not blocked merely because the catalog does not list them; only a missing executable or native transport boundary may stop before that attempt.

## Loop Log

- 2026-09-02 11:16:16: Task initialized by `tools/hermes_workflow_guard.py init-task`.
