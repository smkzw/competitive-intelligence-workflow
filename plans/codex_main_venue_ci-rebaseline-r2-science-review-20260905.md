# Codex Main-Venue Plan: ci-rebaseline-r2-science-review-20260905

Date: 2026-09-05
Objective: 独立审查 v1.3 R2 G01-G09 实现的科学、状态机与合同正确性，重点验证入口消歧、竞品宇宙闭包、按条件触发的两轮恢复、细粒度路由失败、publication/manual-supply 单次中断、原地重命名与 B 类医学语义归并；逐项给出 PASS/VETO 和可复现证据，不做实现修改。

## Task Decomposition

1. Audit the approved v1.3 clauses and G01-G09 acceptance intent.
2. Trace the current implementation and tests for intake, graph, retrieval recovery, universe closure, publication/manual supply, and B semantic grouping.
3. Return per-area PASS/VETO findings with reproducible anchors and minimal remediation contracts.
4. Codex independently verifies findings, implements only accepted repairs with RED/GREEN tests, and reruns the full development gate.

## Source Packet

- `context/ci-rebaseline-r2-science-review-20260905_conference_context.md`
- `docs/specs/competitive-intelligence-workflow-design-v1.3.md`
- `plans/competitive-intelligence-workflow-roadmap-v1.3.md`
- `plans/codex_execution_ci-rebaseline-rebuild-v3.md`
- `src/ci_workflow/`, `tests/`, and `schemas/`
- `runs/execution/ci-rebaseline-rebuild-20260904/worker_03.md` as non-authoritative worker evidence

## Participant Assignments

| Role | Provider | Model | Output |
|---|---|---|---|
| `general_single_object` | `zcode` | `GLM-5.3-Flash` | `runs/conference/ci-rebaseline-r2-science-review-20260905/general_single_object.md` |

## Conference Panel Coordination

- No sub-venue chair. Codex leads the assigned panel directly.

## Main-Venue Review

- Codex performs the final synthesis and acceptance.
- This conference mode has no Reasonix second-review role.

## Timeout And Retry Tracking

- Completed in 1935.111 seconds as `zcode/zcode/GLM-5.3-Flash:max`, session
  `sess_7e85b572-5432-4225-abdd-4891d6ed2a78`; one pass, no fallback, no
  same-session completion round.

## Codex Verification Checklist

- Reproduce every blocking finding against the current bytes.
- Add RED tests before each accepted behavior repair.
- Run focused tests, full Ruff, strict mypy, and the formal fast gate.
- Keep browser/visual acceptance separate from this scientific conference.
- Do not advance M2 or issue release signals while any G01-G09 VETO remains.
