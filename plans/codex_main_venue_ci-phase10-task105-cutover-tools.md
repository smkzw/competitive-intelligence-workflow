# Codex Main-Venue Plan: ci-phase10-task105-cutover-tools

Date: 2026-09-02
Objective: 独立验收 Task 10.5 精准切换工具与 required-v12 owner-stage release receipt 闭环：重点挑战真实旧根零触碰、planned CLI 兼容、多根 registry、无敏感内容读取、路径/symlink/inode/授权/恢复/幂等/残留失败关闭、pre-RC 与 release receipt 分层及 pending/not_applicable 语义；只读，P0/P1 为零才可接受。

## Task Decomposition

1. Audit the exact cutover state machine, path/symlink/TOCTOU/drift boundaries, partial-failure recovery, and all-empty/retain semantics.
2. Audit planned Task 10.7/10.8 CLI aliases and prove no default real target or implicit production write.
3. Audit pre-RC host receipt versus final owner-stage envelope separation, catalog/package/RC/owner/run/session/input/artifact/verdict/time bindings, and optional adapter rules.
4. Challenge tmp-only test isolation and the claim that real legacy/sensitive content was never read.
5. Return severity counts and bounded repair advice; P0/P1 must be zero before acceptance.

## Source Packet

- Task 10.5 PRD/design/implementation packet and approved plan.
- Final tools, schema, tests, package schema declaration, and acceptance note.
- Task 10.4 migration checkpoint/manifest and required-v12 catalog/schema/digest logic.
- Execution worker outputs only as advisory history; current files are authoritative.

## Participant Assignments

| Role | Provider | Model | Output |
|---|---|---|---|
| `general_single_object` | `codebuddy-cli` | `deepseek-v4-flash` | `runs/conference/ci-phase10-task105-cutover-tools/general_single_object.md` |

## Conference Panel Coordination

- No sub-venue chair. Codex leads the assigned panel directly.

## Main-Venue Review

- Codex performs the final synthesis and acceptance.
- This conference mode has no Reasonix second-review role.

## Timeout And Retry Tracking

Record runner duration/session/tool calls and any fallback. One complete pass is expected; use same-session repair verification only for a concrete blocking finding.

## Codex Verification Checklist

- [x] Execution workers completed without fallback and material findings were incorporated.
- [x] Codex pre-conference: focused 24 tests, expanded 162 regressions, Ruff, mypy, package manifest, bundle packaging, and legacy scanner passed at recorded stages.
- [x] Participant independently audited current final files read-only and completed a same-session repair verification.
- [x] Codex applied bounded repairs, reran final suites, and filled review/metrics.
- [x] Same-id review-gate and execution audit passed without warnings.
