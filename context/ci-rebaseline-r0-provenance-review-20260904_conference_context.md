# Conference Context: ci-rebaseline-r0-provenance-review-20260904

Created: 2026-09-04 15:49:26 CST
Objective: Independently audit R0 provenance recovery, strict quality gate truthfulness, historical source-set demotion, zero-contact legacy-boundary correction, immutable recovery snapshot, and disk-hygiene safeguards; return PASS or VETO with file-and-command evidence, without modifying workspace artifacts.
Task type: `high_risk_contradiction_review`
Risk: `high`
Conference mode: `serial`

## Codex Main Venue

- Chair: Codex.
- Duties: understand the real task, decompose, define sources of truth, route work, protect boundaries, verify final artifacts, own visual/browser/PPT/PDF checks, own production writes, and deliver to the user.

## Conference Panel Assignment

- Ordinary tasks remain Codex-direct. Chinese labels or Chinese sentence work uses its declared execution route and does not start a conference.
  - This packet uses one Codex-led conference object (`general_single_object`) with no sub-venue chair. Its effective `CST` route chain is `cursor/default -> opencode-go/muse-spark-1.3-contributor:xhigh -> cms-router/minimax-m3:xhigh -> google-antigravity/gemini-3.8-flash-high:high`; the packet branch is recorded at creation and filtered against the actual execution route nodes recorded below. Before a new session, the runner rechecks the Beijing period; an already-started session is never rerouted.
- Every conference role starts with one bounded same-session pass. Codex reviews its quality and may dispatch zero or more targeted follow-up prompts through the same session. A new session is a routing failure unless a primary role failed before a resumable session existed and the documented fallback was activated.

## Execution-Conference Model Deduplication

- Linked execution task: `ci-rebaseline-rebuild-20260904`
- Execution evidence status: `linked`
- Excluded provider/model nodes: `openai-codex/gpt-5.6-luna`
- If an execution packet exists but runner evidence is missing or unreadable, initialization fails closed. Agent adapters are ignored for this check; provider boundaries and model identity are retained, and effort differences do not bypass deduplication.

## Source Of Truth

- User-approved R0-R6 implementation plan and the 2026-09-04 amendment requiring milestone updates and targeted disk hygiene.
- `docs/governance/r0-provenance-and-quality-gate.md` and `context/ci-rebaseline-rebuild-20260904_recovery_snapshot_receipt.json`.
- `tools/gate.sh`, `tools/check_no_legacy_refs.py`, `tools/verify_rebaseline_source_set.py`, `tools/rebaseline_snapshot.py` and their focused contract/migration tests.
- `context/ci-rebaseline-rebuild-20260904_prechange_inventory.json` and the two frozen `docs/governance/rebaseline-release-source-set-v1*.json` historical records.
- `runs/execution/ci-rebaseline-rebuild-20260904/worker_01.md` is a worker claim to audit, not authority.
- Canonical R1 contracts: `docs/specs/competitive-intelligence-workflow-design-v1.3.md`, `plans/competitive-intelligence-workflow-roadmap-v1.3.md`, and `plans/codex_execution_ci-rebaseline-rebuild-v3.md`.
- Current workspace bytes and reproducible command output are authoritative. The external read-only backup and manifests are verified by Codex and summarized in the receipt; the participant must not leave the workspace to inspect them.

## Scope

- In scope: read-only audit of whether R0 preserves the dirty tree, reports the pre-worker inventory limitation, demotes the 422-file historical set, removes global mypy suppression, records exactly scoped ReportLab ignores, tests the lexical legacy marker without resolving the forbidden target, and establishes a defensible recovery/disk-retention contract.
- In scope: run non-mutating Ruff, mypy, focused tests, gate help/negative checks, Git diff/status and JSON validation inside this workspace where useful.
- Out of scope: editing any file, reading any external directory, checking whether the forbidden legacy root exists, R2-R6 product implementation, visual/scientific acceptance, release source closure, RC freeze, or deleting any artifact.

## Success Criteria

- Each selected primary route returns an auditable output or an explicit health/fallback reason.
- The prompt uses the correct Agent identity, provider/model, effort, tools-enabled policy, and same-session continuation policy.
- The runner records session, usage/tool observations, fallback decisions, and failure reasons without `--max-turns 1`.
- No production path is read or modified; Codex retains final acceptance.
- Return an explicit `PASS` or `VETO`. A PASS must distinguish tested workspace claims from the external backup-state claim that only Codex verified.
- Identify any P0/P1/P2 defect with exact file/line or command evidence and a minimal remediation; do not accept worker_01's report by assertion.
- Confirm no current tool can convert the dirty historical 422-file set into release-ready status and no gate output claims RC/release.
- Confirm cleanup policy cannot authorize broad deletion, removal before evidence binding, deletion of scientific evidence/fixtures/current recovery points, or any legacy-root inventory.

## Parallel Work Rule

For logic-heavy, rigor-sensitive, or artifact-heavy tasks, each participant independently runs the whole bounded workflow and writes a separate output. Leads compare after all available participant outputs are in or explicitly marked pending.

## Timeout Policy

- Participant soft wait: 60 minutes.
- Large-task participant wait: 120 minutes.
- Chair hard wait: 120 minutes.
- Failure rule: Do not fail a model for slow response alone; fail only on terminal error, provider exhaustion/rate limit after controlled retry, empty/truncated retry output, or no useful progress after the high-budget same-session recovery loop. A catalog/auth/transport health preflight timeout or malformed response is diagnostic and must still allow one live route attempt; explicit user routes also proceed when the catalog is stale or incomplete, while a genuinely missing CLI or native transport boundary may block. If a resumable session exists after a step/size boundary, continue it before fallback; repeated identical output/tool evidence triggers the no-progress breaker.
- Pass/turn boundary: one conference prompt is one conference pass. The
  `--max-turns` value controls internal Agent tool-calling turns and is never
  set to 1 for substantive conference execution; generated participant and
  chair commands use the route budgets recorded by the guard.

## Risk Boundaries

- External Agents are advisory; Codex remains final authority.
- Codex owns visual/browser/PPT/PDF/rendered checks, live authority checks, final clinical/regulatory conclusions, and production writes.
- Do not mark a slow model failed solely due to latency.
- Never resolve, stat, list, read, search, or absence-check the forbidden legacy root. Audit only the scanner implementation and its synthetic temporary-directory test.
- Do not inspect the external recovery backup or manifests; report that physical-state verification remains a Codex-owned anchor.

## Loop Log

- 2026-09-04 15:49:26 CST: Conference initialized by `hermes_workflow_guard.py init-conference`.
