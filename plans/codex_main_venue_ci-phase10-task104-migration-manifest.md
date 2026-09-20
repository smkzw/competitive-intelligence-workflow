# Codex Main-Venue Plan: ci-phase10-task104-migration-manifest

Date: 2026-09-02
Objective: 同号正式复核 Task 10.4 迁移清单最终状态与治理关联：确认 59 项测试、精确白名单/排除、敏感哨兵、D01-D70 非运行归档、P0/P1/P2=0，以及不越界到 Task 10.5/10.8；只读。

## Task Decomposition

1. Verify the current post-repair manifest state rather than repeating broad discovery.
2. Challenge the exact migrated/excluded sets, sensitive marker pinning, provenance, archive status, and later-task boundary.
3. Confirm whether any P0/P1/P2 defect remains and report a bounded accept/revise verdict.

## Source Packet

- `migration/legacy_manifest.jsonl`, `migration/legacy_manifest.schema.json`, and `docs/acceptance/migration.md`.
- Migration/contract/fixture tests and `tools/check_no_legacy_refs.py`.
- D01-D70 archive, design spec/ADR anchors, migrated contract/fixture targets.
- Prior review outputs only as history for the repaired findings, not as authority over current files.

## Participant Assignments

| Role | Provider | Model | Output |
|---|---|---|---|
| `general_single_object` | `codebuddy-cli` | `deepseek-v4-flash` | `runs/conference/ci-phase10-task104-migration-manifest/general_single_object.md` |

## Conference Panel Coordination

- No sub-venue chair. Codex leads the assigned panel directly.

## Main-Venue Review

- Codex performs the final synthesis and acceptance.
- This conference mode has no Reasonix second-review role.

## Timeout And Retry Tracking

- Primary pass completed in 230.217 seconds with 45 tool calls, session `9eb008d6-7b25-4b59-8ed6-6d64666bf80f`.
- No timeout, fallback, retry, late output, or same-session follow-up; output incorporated in full.

## Codex Verification Checklist

- [x] Codex pre-run: 59 tests passed, Ruff passed, scanner returned `LEGACY_REF_OK`.
- [x] Participant independently verified final artifacts read-only and returned P0/P1/P2=0.
- [x] Codex filled conference review/metrics and passed review-gate.
- [x] Same-id `audit-execution --require-conference` passed.
