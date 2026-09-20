# Codex Main-Venue Plan: ci-r2-bc-science-acceptance-20260905

Date: 2026-09-05
Objective: 独立审查 B/C fresh research package 到 evidence ingestion、确定性 GateSpec、不可变 report snapshot、独立科学复核绑定和候选 HTML 渲染的真实链路；重点挑战来源/事实/声明闭包、B 门户投影是否可改写医学事实、单臂安全性语义、C endpoint+timepoint 完整性、自我复核禁令、快照幂等及 rendered_unreviewed 边界。仅作审查，不修改代码，不宣称 R2/RC 完成。

## Task Decomposition

1. Reconstruct the actual B and C sequence from package load through render.
2. Challenge package-level closure and independent-review binding.
3. Challenge deterministic gate inputs, blocked behavior, and single-arm/C
   endpoint-timepoint semantics.
4. Verify evidence and report snapshot identities are immutable and reused
   without trusting caller assertions.
5. Verify renderers reopen the prelocked report snapshot and preserve the
   distinction between scientific review and browser/artifact acceptance.
6. Rank findings P0--P3 and propose bounded repairs/tests.

## Source Packet

The authoritative source packet is the context file's Source Of Truth list.
The participant may inspect directly imported storage/domain models and focused
tests only when required to establish a finding. Worker outputs are excluded to
keep reviewer reasoning independent.

## Participant Assignments

| Role | Provider | Model | Output |
|---|---|---|---|
| `general_single_object` | `codebuddy-cli` | `deepseek-v4-flash` | `runs/conference/ci-r2-bc-science-acceptance-20260905/general_single_object.md` |

## Conference Panel Coordination

- No sub-venue chair. Codex leads the assigned panel directly.

## Main-Venue Review

- Codex performs the final synthesis and acceptance.
- This conference mode has no Reasonix second-review role.

## Timeout And Retry Tracking

- Round 1: completed in 397.779 seconds; session
  `980383c6-05cb-4589-af0f-7e9021bb2f63`; no fallback.
- Round 2: same-session continuation completed in 253.350 seconds; no fallback,
  re-dispatch, or force kill.
- Both runs used the 120-minute hard-wait policy; the main thread stayed silent while
  pending.

## Codex Verification Checklist

- [x] Prompt preflight passed.
- [x] Route identity and runner evidence validated.
- [x] Every accepted finding reproduced against current files; stale claims rejected.
- [x] Relevant focused tests rerun after repair (57 passed).
- [x] Full development gate remains green (885 unit/contract tests).
- [x] Conference review and metrics pass `review-gate`.
