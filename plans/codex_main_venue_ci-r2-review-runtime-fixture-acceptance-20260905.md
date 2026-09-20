# Codex Main-Venue Plan: ci-r2-review-runtime-fixture-acceptance-20260905

Date: 2026-09-05
Objective: 独立挑战并验收 R2 两阶段科学复核授权、preview-only 快照、HTML-only 测试分层及真实来源接受边界；输出必须修复、延期和拒绝项，不得宣称 R2 或 RC 完成。

## Task Decomposition

1. Participant independently reads the canonical contracts and actual current
   implementation/tests.
2. Participant attacks the scientific-review trust boundary, preview-only
   separation, HTML-only test layering, and two-run acceptance semantics.
3. Participant classifies findings by severity and proposes the smallest
   evidence-backed amendments, explicitly separating R2 must-fix from R3-R5
   deferrals and YAGNI rejections.
4. Codex reopens cited code/tests, reproduces material findings, decides each
   recommendation, and only then edits or accepts the bounded slice.

## Source Packet

- Canonical design v1.3, formal roadmap v1.3, executable plan v3.
- R2 checkpoint and Codex execution review.
- Current scientific review transition, run service, review receipt/verdict,
  acceptance boundary and real-source acceptance implementation.
- Direct contract/integration/acceptance tests for receipt spoofing, replay,
  self-review, stale content, byte drift, preview snapshots, visual promotion,
  HTML-only layering and external package-digest mismatch.

## Participant Assignments

| Role | Provider | Model | Output |
|---|---|---|---|
| `general_single_object` | `codebuddy-cli` | `deepseek-v4-flash` | `runs/conference/ci-r2-review-runtime-fixture-acceptance-20260905/general_single_object.md` |

## Conference Panel Coordination

- No sub-venue chair. Codex leads the assigned panel directly.

## Main-Venue Review

- Codex performs the final synthesis and acceptance.
- This conference mode has no Reasonix second-review role.

## Timeout And Retry Tracking

- Not dispatched at plan update time.
- Launch exactly once through the guard-generated runner and use its 120-minute
  hard wait. No fixed controller polling or latency-based redispatch.

## Codex Verification Checklist

- Verify participant route identity and runner log.
- Reopen every P0/P1/P2 cited line and related caller.
- Reproduce each claimed defect with a deterministic test or reject it.
- Preserve the three stale external acceptance failures for R5 regeneration.
- Run focused tests and `tools/gate.sh` after any adopted code change.
- Record adoption/rejection rationale; participant cannot self-accept.
