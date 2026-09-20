Continuation round 2 — I'll challenge my previous findings by re-verifying exact code paths in `refresh_service.py` (which I previously only previewed), the plan consistency predicate, and the test's evidence snapshot usage. Plan mode restricts me to read-only actions, which matches this review-only assignment.

Read of the cached artifact was blocked (outside workspace). I'll read the actual source file in the workspace instead.

Round 2 already surfaced a correction: `RefreshPlan` DOES carry `gate_spec_bindings` and `change_records` — contradicting parts of my previous Findings 1 and 3. I must read the rest of the service to verify how they're populated and enforced.

Major corrections surfacing: the plan DOES carry `gate_spec_bindings`, `change_records`, and QC review bundles bind `review_input_digest`. Let me read the rest — `_build_plan`, `_tighten_gates`, `record_gate_decision`, `record_scientific_qc`, `accept_refresh`.

Round 2 is already correcting my previous findings: `record_gate_decision` DOES enforce spec_version/spec_fingerprint against plan bindings (lines 1406-1414), and QC enforces evidence-snapshot binding (line 1507). Let me continue reading the QC and accept paths.

My round-1 findings 1–3 are being contradicted by the actual code — this is exactly what round 2 should surface. Let me finish reading the service and then re-check the test's evidence snapshot usage.

Now let me re-verify the test's evidence-snapshot handling, which is critical to correcting Finding 2.

Confirmed: the test computes the evidence snapshot id (`_evidence_snapshot_id`) and binds it through report manifest → gate result → accept. Finding 2 was wrong. Now let me verify the tightening test path uses the tightened spec for the gate result.

Round 2 has materially corrected my round-1 findings. Let me verify the last two residual findings (QC `valid_until` enforcement, blob JOIN behavior) before writing the updated report.

I now have everything needed. The round-2 verification materially changed my conclusions — three of my round-1 findings were wrong and must be retracted. Here is the complete updated output.

---

# Conference Participant Output: ci-phase9-task92-incremental-refresh-review - general_single_object

## Boundary Check

- Read-only pass, workspace only; no source edits, no production paths, no network, no other participant outputs.
- Did not write the runner-managed report path `runs/conference/ci-phase9-task92-incremental-refresh-review/general_single_object.md`; full report returned below.
- Bash remains unavailable in this session (non-interactive permission denial), so verification is static file inspection only; test execution is not independently confirmed by me and remains a Codex verification need. Not hidden.

## Independent Work Product

### Correction of Round-1 output (most important result of this round)

I challenged my previous answer against the actual code and must **retract or materially narrow three findings** from Round 1. Round 1 relied on a partial read of `refresh_service.py` (preview only); the full read below is authoritative.

**Correction 1 — Round-1 Finding 1 (gate spec binding) is RETRACTED.**
`RefreshPlan` carries `gate_spec_bindings: tuple[GateSpecBinding, ...]` (per-kind `spec_version` + `spec_fingerprint` of the *child* spec, populated in `_tighten_gates`, refresh_service.py:1191-1198), and `record_gate_decision` **does enforce** them:
```python
# refresh_service.py:1406-1414
binding = next((item for item in plan.gate_spec_bindings if item.report_kind is report_kind), None)
if binding is not None and (
    validated.spec_version != binding.spec_version
    or validated.spec_fingerprint != binding.spec_fingerprint
):
    raise RefreshStateError("门槛结果没有使用本轮收紧后的规则版本与内容指纹")
```
The exact scenario I claimed was unguarded — recording a parent-spec PASSED result first — is **tested** (test_incremental_refresh.py:1285-1298 records `parent_spec_result` and asserts `RefreshStateError, match="收紧后的规则"`). The "真实门槛结果绑定" for GateSpec tightening is implemented.

**Correction 2 — Round-1 Finding 2 (evidence snapshot binding) is RETRACTED.**
The binding chain is enforced end-to-end:
- `record_scientific_qc` rejects a report whose manifest evidence id differs from the gate result's (refresh_service.py:1507).
- `accept_refresh` requires, per rebuild kind: `decision.gate_result.evidence_snapshot_id == report_manifest.evidence_snapshot_id`, and when a new evidence manifest is supplied (cutoff expansion), that id must equal `_expected_evidence_snapshot_id(...)` — the content-addressed id of the manifest that will be locked (refresh_service.py:1812-1824, 1904-1923).
- The cutoff-expansion test uses the **computed** id (`_evidence_snapshot_id(evidence_manifest)`, test:452-456, used at 1091, 1101, 1117, 1130) in report manifest, gate result, and accept call. The `"evidence-snapshot-refresh"` string I cited from Round 1 is in the snapshot-registration interruption test only (test:1195), which performs no gate/QC/accept — no contradiction.

**Correction 3 — Round-1 Finding 3 (change records not implemented) is RETRACTED.**
`RefreshPlan.change_records` exists (refresh_service.py:312), auto-populated by `_build_change_records` (promoted→`new`, reuse→`unchanged`, affected→`changed`; caller-declared records merged after validation, 2058-2110), covered by plan validation (complete coverage of affected+reuse, `superseded` must carry successor, reuse must be `unchanged`, promoted must be `new`, 357-373), included in `plan_digest` and the plan event. `withdrawn/revised/superseded` are expressible via `declared_change_records`. The "记录新增、变化、撤回、修订、取代和未变化对象" contract (PRD 范围, §17.2) is satisfied at plan level.

**Correction 4 — Round-1 Finding 4 (QC input digest unverified) is NARROWED.**
`RefreshQcRecord` requires `verdict.review_input_digest == review_bundle.input_digest` (model validator, 526-532) and `record_scientific_qc` re-checks it plus all 12 bundle↔verdict field pairs (1509-1526). The verdict is bound to an actual review bundle. The residual gap is narrower than I stated: the bundle's `source_refs`/`locators` are verified only for mutual consistency, **not** against the evidence database — a self-consistent but fabricated bundle+verdict pair passes the service boundary (the test itself fabricates `"fragment-refresh-1"`). That is a governance boundary, not a broken binding.

### Surviving findings after re-verification

**S1 — QC evidence references are not verified against the evidence snapshot (medium).**
Inference, not observation of failure: `record_scientific_qc` binds verdict↔bundle and bundle↔(snapshot digest, gate key, evidence id) but never checks that `source_refs[*].source_version_id` / `fragment_ids` / `claim_ids` / `fact_version_ids` exist in the registered evidence snapshot's `source_version_ids`/`fragment_ids`/`fact_version_ids` (which are available in the DB-backed manifests). Recommendation: cross-check refs against the evidence manifest at QC-record time (cheap, closes the fabricated-refs path); at minimum, document as an accepted v1 governance boundary.

**S2 — Impact graph is caller-declared; no coverage cross-check against the project (medium).**
`plan_refresh` accepts `impact_nodes`/`impact_edges` and trusts them; guards exist (seeds must be registered; closure must reach claim/page/format; format objects must be `html`; plan validation at 374-379) but nothing verifies the declared graph covers all registered project facts/claims/pages. A sparse edge set silently shrinks the affected set. This is partially a documented design boundary ("输入为稳定 ID 与依赖边"), but the PRD acceptance "影响集合至少能落到事实、声明、页面和格式" is enforced only on the caller's own declaration. Recommendation: for v1, state explicitly that graph registration is orchestrator-owned; a stronger check (compare registered nodes against `content_blobs`/`report_snapshots`/facts inventory) can follow.

**S3 — `_iter_candidates` silently drops blobless DB sources (low-medium, NEW in round 2).**
refresh_service.py:973-980 uses `INNER JOIN content_blobs cb ON cb.content_sha256 = sv.content_sha256`. A `source_versions` row without a `content_blobs` row is silently absent from candidate evaluation — it can never be promoted, with no error. Given migrations 0007 + append-only guards, this state should be impossible; if it occurs, the correct behavior is fail-closed (like the missing date-assertion check at 1010-1013). Recommendation: `LEFT JOIN` + explicit missing-blob failure, or document the invariant.

**S4 — QC validity window is not enforced (low).**
`ScientificQcVerdict.valid_until` is never read by the service (grep confirms only `reviewed_at` is used, as event timestamp). A verdict whose validity window has lapsed is accepted indefinitely. Recommendation: enforce `reviewed_at <= accept time <= valid_until` at `accept_refresh`, or document why the field is inert for v1.

**S5 — Coverage gaps, unchanged from round 1 but re-verified:**
- Combined cutoff-expansion + gate-tightening path (`change_kinds` supports both; `_impact_sets` merges seed sets) has no test.
- Veto-QC path (`verdict != "accepted"` blocks accept at 1826-1832) has no test.
- Page nodes with multiple `report_kinds` over-expand `rebuild_report_kinds` conservatively (possible accept-blocking surprise for shared pages).
- Cosmetic: `refresh_reevaluate` declares `writes=("evidence",)` with `side_effect_class="none"` (refresh.py:205-211); refresh nodes are declarative-only, not registered in `graph/registry.py` (acceptable v1 boundary).

**S6 — Process/evidence trail still empty (HIGH for the review, unchanged).**
`metrics/ci-phase9-task92-incremental-refresh_execution_metrics.md` and `reviews/codex_execution_..._review.md` remain all TODO; worker reports `runs/execution/ci-phase9-task92-incremental-refresh/` do not exist; `task.json` is `in_progress`, `commit: null`. A pytest-9.1.1 `__pycache__` proves the test module imported at least once, not GREEN. PRD 验收 6 (specified tests, shared regressions, Ruff, mypy) has no recorded evidence.

## Evidence And Assumptions

**Observation (verified by full file read this round):**
- Spec binding: refresh_service.py:1406-1414; bindings built at 1191-1198; test asserts parent-spec rejection at test:1285-1298.
- Evidence binding chain: refresh_service.py:1507, 1812-1824, 1904-1923; test uses computed id at test:452-456, 1091-1130.
- Change records: model 246-289, 312; auto-build 2058-2110; validation 357-373; test coverage asserted via plan checks.
- QC bundle binding: model 526-532; service 1509-1526.
- Fail-closed accept ordering: rebuild receipts → gate pass → snapshots → evidence snapshot → QC → flip/event/claim (1759-1880).
- Idempotency/recovery: content-idempotent `persist_project_contract` (migrations.py:119-148); content-addressed idempotent `SnapshotStore._lock` (snapshot_store.py:200-227); EventStore dedup by event_id and idempotency key (event_store.py:204-238); receipt self-heal (1363-1386).
- Schema dependencies exist in migrations 0002-0009 with append-only triggers.
- `valid_until` absent from service (grep). `INNER JOIN content_blobs` at 978. `source_refs` only pairwise-checked at 1520.

**Inference (labeled):** S1-S5 are static-analysis conclusions; not executed. My Round-1 corrections (1-4 above) supersede the corresponding Round-1 text.

**Assumptions:** The test file read reflects the final working tree; Codex will re-run the suite to confirm GREEN; code state matches the review (no uncommitted drift assumed beyond what is visible).

## Risks, Gaps, And Verification Needs

1. **Run and record the suite (blocking):** `pytest tests/integration/test_incremental_refresh.py tests/integration/test_historical_cutoff.py tests/reports/test_gate_override_strictness.py tests/contract/test_project_contract.py`, plus `ruff` and `mypy`. Record outcomes in the metrics file. I could not execute in this session.
2. **Adjudicate S1-S4:** S1/S3 are small, high-value hardening; S4 is a one-line guard or a documented decision; S2 needs an explicit boundary statement.
3. **Confirm minimal-diff boundary:** no new migration was added and `refresh_project_contract` pre-existed; confirm no other shared file edits beyond justified reasons.
4. **Add the two untested paths (S5)** if the task is to remain Green-to-next-phase: combined cutoff+gate, veto-QC.
5. **Retain my corrected conclusion prominently:** Round-1 findings 1-3 are false; the implementation is materially stronger than my Round-1 report implied.

## Recommended Next Step

Codex should: (1) execute the verification suite and record evidence in `metrics/`; (2) accept the corrected binding analysis (spec fingerprint, evidence snapshot chain, change ledger are implemented and tested) and treat only S1-S6 as open review items; (3) decide S1-S4 as either fixes or documented v1 governance boundaries; (4) add the two missing test paths if time-budget allows; (5) after GREEN, complete the execution review and `cleanup-execution` archive. I can provide a bounded follow-up detailing the minimal diffs for S1/S3/S4 on request.

**Bounded questions for Codex:**
- Q1: Do you want S1 (QC source-ref cross-check against the evidence snapshot) implemented now, or documented as an orchestrator-governance boundary for v1? It changes the QC record contract.
- Q2: For S3, should a missing `content_blobs` row be a hard fail-closed error, or is the invariant already guaranteed upstream so the silent JOIN is acceptable? This affects `_iter_candidates` behavior only.
- Q3: Is `valid_until` intended to be enforced at accept time in v1, or is it future-proofing? If the former, I recommend the one-line guard at `accept_refresh`.
- Q4: Should the combined cutoff+gate and veto-QC paths be added as tests before this task is accepted, or deferred?
