All checks are in. Compiling the verification matrix before writing the report:

- **GT01 + two exact Task 3.5 nodes**: `uv run pytest tests/graph/test_transition_matrix.py tests/graph/test_partial_delivery.py tests/graph/test_partial_delivery_blocked.py -q` → **8 passed**
- **Full repo**: `uv run pytest tests -q` → **445 passed**
- **Gates**: ruff clean, mypy strict clean (63 files)
- **My independent probe** (`/tmp/ci_r2_probe/probe_r2.py`, system temp): all 8 checklist items + regressions → **ALL PROBE CHECKS PASSED**
- **Negative probe** (`/tmp/ci_r2_probe/probe_neg.py`): direct-jump does NOT over-fire when continuable objects remain
- **One new finding** (stale-version forged rebind read path) — assessed against the round's explicit scope line

Here is the complete report for the runner to persist at `runs/conference/ci_phase3_task35_acceptance/general_pi_qwen38_round2.md`:

---

# Conference Participant Output: ci_phase3_task35_acceptance - general_pi_qwen38 (Round 2)

## Boundary Check

- Read-only: only the permitted files were read (`AGENTS.md`, spec v1.2, `recovery.py`, `transitions.py`, `guards.py`, `executor.py`, `reducer.py`, three test files). No repo file edited. Probes written only under system temp (`/var/folders/.../ci_pi_r2_*`). No worker reports, Codex reviews, or other participant outputs read.
- Per the round-2 scope line, "raw accepted events directly writable to the shared event store" is NOT treated as a blocker; functional event integrity and real recovery remain in scope and were re-attacked.

## Independent Work Product

Changed surface since round 1 (verified by `git diff`): `transitions.py` adds two edges `running/awaiting_user -> partial_delivery_blocked` reusing trigger `remaining_selected_blocked` and guard `g_project_partially_delivered_partial_delivery_blocked`; `test_transition_matrix.py` GT01 fixture gains the matching two literal edges. `recovery.py` (untracked, 1749 lines) now has: direct-jump reconcile ordering; authoritative-version gate on `conditions()`; stale-version rejection on all public paths; per-source-state reopen generations (`_entry_generation`, `_last_accepted_reopen`); `_version_at_blocked` fallback to the latest binding at/before the block event; whitespace normalization checks in `_validate_rebind_event`; fresh-view recomputation after rebind append.

Verification methods (all my own, project venv, system temp):
1. Ran GT01 exact node + both Task 3.5 exact nodes: **8 passed** (23.2 s).
2. Ran full suite: **445 passed**; ruff + strict mypy clean.
3. Wrote and ran an independent probe script covering all 8 checklist items plus regression attacks (forged selection/rebind events, whitespace contract ids, unbound-version format reopen).
4. Wrote a negative probe proving the new direct-jump edges do not over-fire.

## Checklist Results (each item re-reproduced independently)

| # | Requirement | Result | Evidence |
|---|---|---|---|
| 1 | `running`: A-HTML delivered + B blocked → direct `partial_delivery_blocked`; A-only HTML delivered + PPTX blocked → direct; `awaiting_user` equivalent | ✅ | Probe 1a/1b/1c: accepted event `from_state` = running/awaiting_user, `to_state` = `partial_delivery_blocked`; `"partially_delivered" not in project_transition_states` in all three; canonical state matches; terminal replay appends nothing |
| 2 | Reopen from `partial_delivery_blocked`, nothing actually recovered → silent reconcile returns to the terminal state, not stuck in `running` | ✅ | Probe item 2: reopen accepted → `running`; next reconcile accepted `running -> partial_delivery_blocked`; canonical state terminal again |
| 3 | v1 bound, then v2 bound → every public path rejects stale v1; same-version selection drift fails closed | ✅ | Probe item 3: bindings `[1, 2]` in order; `reconcile/conditions/reopen_project/reopen_format/rebind_report` all raise `ContractDriftError` for v1; v2 with changed selection raises `ContractDriftError` and appends no event; v2 remains authoritative |
| 4 | Raw forged rebind with trailing/duplicated whitespace in old/new ids rejected by unified validation | ✅ | Probe 4a (`report_B ` / `report_B_v2 `) and 4b (`report_B  _v2`) → `CoordinatorEventContractError` before any target resolution |
| 5 | Two consecutive `awaiting_user -> running` reopens each accepted; per-generation replay idempotent; reason drift rejected | ✅ | Probe item 5: two distinct accepted reopen event ids; exactly two accepted `awaiting_user -> running` events; replay adds no events; drifted reason → `EventConflictError` per cycle; final state `running` |
| 6 | Format blocked under v1 with no `contract_version` in block evidence → v1 cannot use `new_contract_version_reopens`; after binding v2 → allowed | ✅ | Probe item 6: verified the stored block event's `guard_evidence` lacks `contract_version`; v1 reopen raises `CoordinationError`; after binding v2 (reconcile binds while project is terminal), v2 reopen accepted → format `queued`. Boundary probe 6b: no prior binding at all → still denied (version unprovable, fail-closed) |
| 7 | `rebind_report` result conditions already resolve the new target | ✅ | Probe item 7: result `conditions.target_matrix` contains `report_B_v2`, not `report_B`; old object remains `evidence_blocked`; replay → `replay_noop` |
| 8 | GT01 exact node + two Task 3.5 exact nodes pass | ✅ | 8 passed; full repo 445 passed |

Negative over-fire probe: with a delivered artifact **and** a continuable object remaining, `running` goes to `partially_delivered` (not the new terminal jump) and `awaiting_user` stays with no candidate — the new edges only fire when `no_running_selected_object` + `remaining_selected_exhausted_blocked` + `at_least_one_artifact_delivered` all hold mechanically.

## Original P0/P1 Status

All original P0/P1 items from round 1 are **eliminated**, each confirmed by my own reproduction above (items 1–7 map to those findings):
- P0 stuck-terminal paths (running/awaiting_user could not reach `partial_delivery_blocked`; reopen could not fall back) → fixed by the two new declared edges + reconcile ordering; verified items 1, 2.
- P0/P1 stale-contract read/write paths → fixed by `_require_authoritative` + version gate in `_ensure_selection_bound`; verified item 3.
- P1 reopen identity collisions across `awaiting_user` generations → fixed by per-source-state generation identity; verified item 5.
- P1 unprovable format block version → fixed by `_version_at_blocked` binding-position fallback with fail-closed when unprovable; verified item 6/6b.
- P1 whitespace-normalization asymmetry in rebind ids → fixed by read-path normalization checks; verified item 4.
- P1 rebind result computed from stale view → fixed by fresh-view recomputation; verified item 7.

## Remaining Functional P0/P1

**None found.** No functional P0/P1 reproduces against the current source.

## P2 Findings (non-blocking, with attribution)

**P2-1 — Unified rebind read path does not enforce the stale-version rule the write path enforces.** `_validate_rebind_event` accepts a `coordinator.report_target_bound` whose `contract_version` matches a once-bound (but no longer latest) binding; the write path (`_ensure_selection_bound`) would have rejected that version. Minimal repro (system temp): bind v1 then v2 (same selection), reopen project under v2, then `store.append` a structurally complete rebind claiming `contract_version=1` for `report_B -> report_B_v2`; `conditions(v2)` does not raise and target resolution advances under the stale version. No legitimate public path can produce such an event (verified), and manifesting it requires raw event-store appending — the capability the round explicitly de-scoped as security hardening — hence P2, not P1. Minimal remediation (~6 lines): pass the running `seen_contracts` map into `_validate_rebind_event` and raise `CoordinatorEventContractError` when `payload["contract_version"] < seen_contracts[contract_id]` max version at that event position — mirroring the write-path rule. Attribution: Task 3.5 follow-up or a future event-integrity hardening task.
**P2-2 — Hygiene:** `DeliveryContract.contract_id` accepts non-normalized whitespace (`"contract_i8 "`), creating inert parallel contract-id namespaces. Fail-closed (reads under the unpadded id raise "未绑定"), no drift possible; optionally reject non-`" ".join(id.split())` ids in `__post_init__`. Attribution: same follow-up.

## Evidence And Assumptions

- Evidence: test runs (8 passed / 445 passed), ruff/mypy clean, probe transcripts (all checks passed; negative probe passed; stale-version repro produced `FAIL stale-version rebind accepted` as documented for P2-1). All probes under `/var/folders/.../ci_pi_r2_*` system temp; no production or repo writes.
- Assumption: the round-2 checklist (items 1–8) is the authoritative acceptance contract for this pass, per Codex's follow-up prompt.
- Inference: since no public API path can emit a stale-version rebind (write path raises first), P2-1's impact is confined to adversarial raw appends; classified under the round's explicit scope exclusion.

## Risks, Gaps, And Verification Needs

- If Codex later re-includes adversarial event-store integrity as a blocking criterion, P2-1 should be promoted and fixed before acceptance (remediation above is minimal and deterministic).
- Not in scope here (unchanged): report portal/format rendering, CLI/fixtures, Task 3.6/3.7, browser/PDF/PPT/visual, scientific QC.

## Recommended Next Step

1. Codex accepts Task 3.5 on this evidence (P0=0, P1=0).
2. File P2-1 (stale-version rebind read-path check) and P2-2 (contract-id normalization) into the event-integrity hardening backlog or the Task 3.7-adjacent follow-up; neither blocks.

## Verdict

**PASS**

`P0=0; P1=0; P2=2`
