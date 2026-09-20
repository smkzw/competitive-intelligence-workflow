Round 3 — final pass. I have completed full-file verification in round 2; this round I resolve the round-1/round-2 contradictions explicitly, add one newly identified edge case, and give Codex an actionable final recommendation. (Note: the workflow-state hook referencing task-91 is stale for this session — I am the task-92 review participant and take no action on it; plan mode is respected, this deliverable is text-only.)

---

# Conference Participant Output: ci-phase9-task92-incremental-refresh-review - general_single_object

## Boundary Check

- Read-only audit, workspace only; no source edits, no production paths, no network, no other participant outputs, no writes to the runner-managed report path. Plan mode respected (text deliverable only).
- Bash unavailable this session (non-interactive permission denial) → verification is static file inspection; test execution unconfirmed by me and handed to Codex as a blocking verification need. Not hidden.
- No secrets encountered.

## Independent Work Product

### Explicit resolution of round-to-round contradictions

| Round-1 finding | Final status | Resolution evidence |
|---|---|---|
| F1: gate result not bound to child spec | **RETRACTED** | `plan.gate_spec_bindings` carries child `spec_fingerprint`; `record_gate_decision` enforces it (refresh_service.py:1406-1414); test asserts parent-spec rejection (test:1285-1298) |
| F2: evidence snapshot not bound at accept | **RETRACTED** | Chain enforced: gate result → report manifest → expected/locked evidence id (refresh_service.py:1507, 1812-1824, 1904-1923); test uses computed id (test:452-456, 1091-1130) |
| F3: change ledger missing | **RETRACTED** | `RefreshPlan.change_records` auto-built and validated (refresh_service.py:246-289, 312, 357-373, 2058-2110); included in `plan_digest` |
| F4: QC input digest unverified | **NARROWED** | Verdict must match bundle `input_digest` + 12 field pairs (model 526-532; service 1509-1526). Residual: `source_refs`/`locators` checked for self-consistency only, not against evidence DB (→ S1) |
| F5: format propagation not required when pages affected | **STANDS, subsumed into S2** | Only guard is “affected must include claim/page/format” (374-379); page→html edge omission is not detected |

Root cause of the round-1 errors: round 1 relied on a preview of `refresh_service.py`; the full read in round 2 contradicted it. The implementation is materially stronger than round 1 reported. This corrected conclusion should be treated as authoritative.

### Surviving findings (final)

**S1 — QC evidence references not verified against the evidence snapshot (medium).**
Verdict/bundle `source_refs[].source_version_id` and fragment/claim/fact ids are pairwise-consistent only; the registered evidence snapshot's `source_version_ids`/`fragment_ids`/`fact_version_ids` (available in DB manifests) are never consulted. A self-consistent fabricated bundle+verdict passes the boundary. Fix: cross-check refs against the evidence manifest in `record_scientific_qc` (small, closes the fabricated-refs path) — or document as accepted v1 orchestrator-governance boundary. Decision needed.

**S2 — Impact graph is caller-declared; no coverage check against the project (medium).**
`impact_nodes`/`impact_edges` are trusted inputs; guards (seeds registered, closure must reach claim/page/format, html-only formats) do not detect a sparse graph that omits facts/edges, which silently shrinks the affected set. Subsumes round-1 F5. Fix: v1 statement that graph registration is orchestrator-owned; later pass could compare registered nodes against project inventory (facts/claims/pages/snapshots).

**S3 — `_iter_candidates` silently drops blobless DB sources (low-medium, new in round 2).**
`INNER JOIN content_blobs` (refresh_service.py:978) — a `source_versions` row without a blob is silently unevaluated and can never be promoted; no error. Invariant should make this impossible (migrations 0007 + append-only guards); if it can occur, the date-assertion check (1010-1013) shows the intended fail-closed pattern. Fix: `LEFT JOIN` + explicit failure, or document the invariant.

**S4 — QC validity window not enforced (low).**
`ScientificQcVerdict.valid_until` is never read by the service (grep: only `reviewed_at` is used). Fix: guard `reviewed_at <= accept time <= valid_until` in `accept_refresh`, or document the field as inert for v1.

**S5 — Test coverage gaps (low-medium).**
Combined cutoff+gate path (structurally supported: change_kinds both, `_impact_sets` merges seeds at 1240) untested; veto-QC path untested; multi-kind page over-expands `rebuild_report_kinds` conservatively; cosmetic `refresh_reevaluate` writes/side_effect_class mismatch; refresh nodes not wired into `graph/registry.py` (declarative-only v1 boundary).

**S6 — Execution evidence trail empty (HIGH, process).**
Metrics/review TODO; worker reports absent; `task.json` `in_progress`, `commit: null`; pyc proves import only. PRD 验收 6 (specified tests + shared regressions + Ruff + mypy) has no recorded evidence.

**S7 — NEW: two pending plans may target the same child version (low).**
If a cutoff-expansion plan (child v2) is pending and a second `plan_refresh` produces a *different* refresh_id but an *identical* child contract (same cutoff content), it is allowed (persist idempotent by content) and both plans may later accept to v2; `_flip_active_contract` no-ops on the second (`active == child`, 1929-1930), recording two `refresh.version.accepted` events for one version. Content-differing second plans fail closed (`MigrationDriftError`). Fix options: reject a second plan while a pending plan exists for the active version, or make the accept path verify the accepted plan is the only one for that child version.

## Evidence And Assumptions

**Verified by full read (observation):**
- Binding chain and change ledger: as tabled above (file/line references).
- Fail-closed accept ordering: rebuild receipts → gate pass → missing decisions → snapshots → evidence snapshot → QC → flip/event/claim (refresh_service.py:1759-1880).
- Idempotency/recovery primitives: content-idempotent `persist_project_contract` (migrations.py:119-148); content-addressed `SnapshotStore._lock` (snapshot_store.py:200-227); EventStore dedup by event_id/idempotency key (event_store.py:204-238); receipt self-heal (1363-1386).
- Migrations 0002-0009 provide all referenced tables with append-only triggers; no new migration needed.
- Test helpers/policies/fixtures all exist and match the models (`pythonpath=["."]` makes cross-test import collectable).
- `refresh_project_contract` pre-existed (also used by `tests/contract/test_project_contract.py`); ADR 0013 and spec §17.2 match scope.

**Inference (labeled):** S1-S5, S7 are static-analysis conclusions, not executed; S6 is a recorded-state observation.

**Uncertainty:** (1) Test GREEN/Ruff/mypy unverified by me — the strongest single uncertainty; (2) whether upstream invariants make S3 unreachable; (3) whether the orchestrator ever runs two pending plans (S7) — possible in principle, absent from tests; (4) static analysis cannot rule out runtime-only issues (SQL, datetime edge cases, SQLite behaviors).

## Risks, Gaps, And Verification Needs

Blocking (acceptance):
1. Run and record: `pytest tests/integration/test_incremental_refresh.py tests/integration/test_historical_cutoff.py tests/reports/test_gate_override_strictness.py tests/contract/test_project_contract.py`; `ruff`; `mypy`. Populate `metrics/ci-phase9-task92-incremental-refresh_execution_metrics.md` and the execution review. This also closes the round-1-to-3 evidence gap (S6).
2. Adjudicate S1-S4 as fix-or-document; S7 needs a one-line policy decision.
3. Confirm minimal-diff boundary (no migration changes; shared-file changes limited to justified reasons).

Non-blocking:
4. Add combined cutoff+gate and veto-QC tests (S5).
5. Optionally harden S1/S3/S4 per decisions in Q1-Q3.

## Recommended Next Step

Ordered, actionable for Codex:
1. Run the verification suite and record results (closes S6; confirms GREEN before any further work).
2. Accept the corrected binding analysis — spec fingerprint, evidence-snapshot chain, and change ledger are implemented and tested; do not re-litigate F1-F3.
3. Decide S1-S4 via the questions below (each is a small diff or a documented boundary); S7: reject concurrent pending plans for the same active version.
4. Add the two missing test paths (S5) if budget allows.
5. After GREEN and decisions, complete the execution review verdict and run `cleanup-execution` archive; the conference review file can then record this participant's final corrections.

**Bounded questions for Codex:**
- Q1 (S1): Implement the QC source-ref cross-check against the evidence snapshot now, or document orchestrator-governance as v1 boundary?
- Q2 (S3): Treat a missing `content_blobs` row as fail-closed (LEFT JOIN + error), or is the invariant guaranteed upstream so the silent JOIN is acceptable?
- Q3 (S4): Enforce `valid_until` at accept time, or document it as inert for v1?
- Q4 (S7): Add a guard against a second pending plan targeting the same child version, or accept the current first-wins flip semantics and record it as a known constraint?

This completes my final pass. All round-1 errors are explicitly resolved above; evidence, inference, recommendation, and uncertainty are separated; Codex retains final authority.
