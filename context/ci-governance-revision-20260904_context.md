# Task Context: ci-governance-revision-20260904

Created: 2026-09-04 13:35:19
Objective: 核验 ZCode 工程审计与八项候选裁决，结合当前暂停现场和既有构建证据，形成可追溯的采纳矩阵，并在用户澄清后修订路线图、设计文档与执行计划。
Task type: `stage_review_plan`
Risk: `high`
Selected agent route: `codex` / `gpt-5.6-sol` / `medium`

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

- 2026-09-04 13:35:19: Task initialized by `tools/hermes_workflow_guard.py init-task`.
