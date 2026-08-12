All evidence gathered. Final reassessment:

# Conference Participant Output: ci_phase3_task34_acceptance - general_pi_qwen38

Round 4 — single-issue fix verification: can a raw `graph.node.completed` appended directly to the shared EventStore still bypass `GraphExecutor.complete_node()` and poison canonical state? Same Pi/Qwen session; no restart.

## Boundary Check

- Read-only. Re-read only the changed surface: `reducer.py` (new validation), `executor.py` (`complete_node` + canonical JSON for parity check), `test_checkpoint_replay.py` (expanded GT11). Probes wrote only to a `tempfile.mkdtemp()` system temp dir; no repo file touched.
- No worker report, Grok output, or Codex conclusion read. Runner-managed report path not written.

## Independent Work Product

**1. Code inspection of the fix.**
- `graph_reducer` now calls `_validate_node_completed(event)` **before** `_apply_node_completed` (`reducer.py:343-345`), and `_validate_accepted_transition(state, event)` before applying transitions (`reducer.py:335-336`). Unknown `graph.*` types raise `GraphEventContractError` (`reducer.py:329-331`).
- `_validate_node_completed` (`reducer.py:236-317`) re-checks every field the public boundary enforces, in equivalent order: `node_id`/`input_digest`/`completion_digest` non-blank → `node_contract()` lookup → `scope == contract.scope` → report_kind ∈ {A,B,C} for report/artifact scope / must be None for shared → exact output key set vs declared → completion predicate → `validate_typed_outputs` → recomputed `completion_digest` → recomputed `event_id` via `stable_id("graph-node-completed", project, run, node, report-or-shared, input_digest)` → recomputed idempotency key format. `_canonical_json_bytes` (`reducer.py:136-150`) is byte-identical in parameters to executor `_canonical_json` (`executor.py:48-61`); input_digest normalization (`" ".join(split())`) matches both sides.
- Ordering guarantee: in `CheckpointStore.replay` the reducer runs before `side_effect(event)` and before checkpoint save, so a forged event fails closed with zero checkpoint and zero side effect.

**2. Independent probes (temp dir, production code) — original reproducer and variants.**
- **R1** forged payload `gate`/A, `gate_passed="YES"`, `failures="not-a-list"`, `evidence_digest=""`, appended raw to EventStore: `GraphExecutor.state()` → `GraphEventContractError: gate 输出类型不合法`; no checkpoint file created.
- **R2** same forged event: `CheckpointStore.replay()` → same `GraphEventContractError`, checkpoints dir remains empty.
- **R3** mixed stream (legal `complete_node("resolve")` first, forged gate event appended after): `state()` still fails closed — a single forged event contaminates nothing and is not silently skipped.
- **R4** legal event replay: `complete_node("gate", …)` by one executor; a **fresh** executor's `state()` and `CheckpointStore.replay()` both accept it; `gate.A == {gate_passed: True, failures: [], evidence_digest: d…}`; event in `applied_event_ids`. Not a blanket rejection.

**3. Approved exact nodes.**
- `pytest tests/graph/test_checkpoint_replay.py::test_replay_never_duplicates_publish_move_approve_or_delete -q` → `1 passed in 0.24s`.
- `pytest tests/graph/ -v` → `11 passed in 24.88s` (all 11 exact GT nodes listed individually, all PASSED).

**4. GT11 now covers the requested contract directly** (`test_checkpoint_replay.py:533-788`): forged output types (including the exact `gate_passed="YES"` reproducer), scope mismatch, report_kind mismatch, shared+report_kind, missing/extra output keys, predicate failure, completion_digest drift, event_id drift, idempotency_key drift — each asserted to raise `GraphEventContractError` with **no checkpoint persisted** (`:359`); plus legal-event replay counter-cases for both transitions (`:495-531`) and node completions (`:762-788`).

## Evidence And Assumptions

- The round-3 hole (raw append bypassing `complete_node`) is closed at both canonical-state paths: `state()` (R1/R3) and `replay()` (R2). Validation lives in the reducer, so it is enforced by every consumer of the event stream, not only by the executor write path. Assumption held: no other call site applies node outputs without the reducer (grep-level read of `reducer.py` confirms `_apply_node_completed` has one caller).
- Transition forgery got the symmetric treatment (`_validate_accepted_transition` with declared-edge, trigger, guard_id, current-state, and guard re-evaluation checks; GT11 cases 1–7). This is beyond my single requested item but consistent with it; I verified it only to the extent of the test evidence plus code read — it raises the same fail-closed error before state mutation.
- Version-pinning caveat documented in code (`reducer.py:168-170`, `244-246`): event `schema_version=1.0` is frozen against the current registry/node contracts; future contract versioning must not weaken replay validation. Acceptable for Task 3.4.

## Risks, Gaps, And Verification Needs

- **P2 (carried, unchanged):** non-target side-effect operation fields (`decision` on approve; `path`/`source_path`/`destination_path`) still raise bare `KeyError` rather than a `SideEffectError`-family domain error. No new evidence this round; behavior remains fail-closed with no duplication and no checkpoint advance, so it stays P2 per the round-2 classification and the instruction not to upgrade without new evidence. Suggested minimal fix (helper `_required_str` raising `SideEffectError`) already proposed in round 2; assign to the Task 3.5 producer-wiring follow-up.
- No P0/P1 identified in the reviewed fix. The validation is per-event and deterministic; worst case for a malformed stream is a fail-closed replay, matching the v1.2 fail-closed principle.

## Recommended Next Step

1. Codex closes this single-issue review: fix verified by exact approved nodes (11/11 green) plus four independent probes; forged `graph.node.completed` can no longer reach canonical state or checkpoints through either `state()` or `replay()`.
2. Track the one carried P2 (`_required_str` error-type hygiene) under Task 3.5 producer wiring; no re-conference needed for it.

## Verdict

PASS

P0=0; P1=0; P2=1
