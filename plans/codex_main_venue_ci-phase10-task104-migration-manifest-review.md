# Codex Main-Venue Plan: ci-phase10-task104-migration-manifest-review

Date: 2026-09-02
Objective: 独立审查 Task 10.4 最终迁移清单闭环：验证 10 项白名单、11 类排除、敏感哨兵、目标摘要、D01-D70 非运行归档与 Task 10.5/10.8 边界；只读，P0/P1 为零才可建议接受。

## Task Decomposition

1. Independently challenge manifest closure and sensitive-data semantics.
2. Verify exact whitelist/exclusion coverage and migrated target integrity.
3. Verify the preserved decision ledger and non-runtime boundary.
4. Verify that Task 10.4 does not claim Task 10.5 cutover or Task 10.8 absence/release acceptance.
5. Apply only bounded repairs, rerun deterministic checks, and request same-session delta review when necessary.

## Source Packet

- Manifest/schema, migration acceptance note, closure tests, legacy-dependency scanner, preserved D01-D70 archive, design/ADR provenance, and internalized targets named by the manifest.
- Sensitive legacy contents are excluded from the read set; only fixed public sentinel declarations and their digests may be inspected.

## Participant Assignments

| Role | Provider | Model | Output |
|---|---|---|---|
| `general_single_object` | `codebuddy-cli` | `deepseek-v4-flash` | `runs/conference/ci-phase10-task104-migration-manifest-review/general_single_object.md` |

## Conference Panel Coordination

- No sub-venue chair. Codex leads the assigned panel directly.

## Main-Venue Review

- Codex performs the final synthesis and acceptance.
- This conference mode has no Reasonix second-review role.

## Timeout And Retry Tracking

- Primary pass completed in 268.326 seconds with 43 tool calls and identified one P1 plus two P2 findings.
- Codex applied bounded repairs and resumed the same CodeBuddy session; round 2 completed in 75.399 seconds with 9 tool calls.
- No timeout, fallback, replacement session, or late output. Both outputs were incorporated; round 2 supersedes the initial severity verdict.

## Codex Verification Checklist

- [x] Participant stayed read-only and inside the authorized CWD.
- [x] Exact 10 migrated items and all 11 exclusion categories verified.
- [x] Sensitive markers are declaration-derived and digest-pinned without reading source contents.
- [x] D01-D70 archive and non-runtime status verified.
- [x] Provenance anchors and current-observation/frozen-snapshot distinction verified.
- [x] Migration suites, related contract regressions, Ruff, and legacy scanner run by Codex.
- [x] Final P0/P1/P2 counts are zero; no real cutover/delete or RC claim was made.
