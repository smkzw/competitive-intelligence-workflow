Re-reading the current reducer, executor, and tests first, then I’ll run the 11 exact nodes plus temp-dir probes for delete identity and raw event forgery.Fixes are in the current sources. Next I’ll check GT11 coverage and run the eleven nodes plus temp-dir probes.The 11-node suite is still running. I’ll write independent temp-dir probes now and collect pytest when it finishes.All 11 approved nodes passed. Running the independent temp-dir probes next.# Conference Participant Output: ci_phase3_task34_acceptance - general_grok45

## Boundary Check

- Same Grok Build session `8d0d63cd-72a0-421c-af9f-1f77c9ac4356`, role `general_grok45`. Targeted re-verification of the two prior P1s against **current** files only. No restart.
- Read-only in `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`. Workspace source/tests/context/plans/Trellis/reports were not edited. Probe script and artifacts lived only under `/tmp` (`/tmp/ci_t34_round4_probe.py`, `/tmp/ci_t34_r4_uf5j211y`).
- Runner path `runs/conference/ci_phase3_task34_acceptance/general_grok45_round4.md` was not written by tools.
- Pi output, worker reports, and Codex conclusions were not read.
- Visual / PPT / browser / clinical-regulatory acceptance was not performed. Codex remains final authority.

**Re-read this round:** `src/ci_workflow/graph/{reducer,executor,registry}.py`; `tests/graph/test_checkpoint_replay.py` (GT11 extensions). Prior-session packet knowledge used only as contrast, not as current-defect evidence.

**Executed this round:**

| Command | Result |
|---|---|
| `.venv/bin/pytest` on the 11 exact node ids | `11 passed in 23.43s`, exit 0 |
| `/tmp/ci_t34_round4_probe.py` | `total=23 pass=23 fail=0`, exit 0 |

## Independent Work Product

### Prior P1s versus current files

The previous report scored two P1s against **pre-fix** sources. Those findings must not be carried forward if the current code and probes close them.

| Old P1 | Current status |
|---|---|
| `artifact.delete` target identity disagreed between reducer (`approval_id` fallback) and `_delete` (`path` fallback) | **Closed.** Both call `derive_side_effect_target` (`reducer.py` 99–125, 348–352; `executor.py` 23, 194, 211, 230, 256). |
| Raw `graph.transition.accepted` applied `to_state` with no matrix/guard/current-state check | **Closed.** `_validate_accepted_transition` runs before any state write (`reducer.py` 157–233, 335–340). |

### 1. Shared target identity and path-only delete

`derive_side_effect_target` is the single rule:

- `revision.approve` → non-blank `approval_id`
- `artifact.publish` / `artifact.move` → non-blank `target_identity`
- `artifact.delete` → non-blank `target_identity`, else non-blank `path`
- Missing/wrong type → `SideEffectTargetError`, not `KeyError`

**Independent probe (`/tmp/ci_t34_r4_uf5j211y`):**

- Path-only payload `{"path": "staging/gone.txt"}`: effect deleted the file; crash before checkpoint; ledger already had one line; recovery replay added **no** second ledger line; `side_effects["staging/gone.txt"]` recorded; second replay returned the same checkpoint.
- Empty delete payload: `SideEffectTargetError: artifact.delete 需要非空 target_identity 或 path`; spy side-effect **not** called; file kept; no checkpoint file.
- Prefer `target_identity` over `path` when both present.

GT11 now contains the same path-only stream plus five malformed-target cases (`test_checkpoint_replay.py` 220–303). Combined with the 11-node run, this is no longer table-only coverage.

### 2. Raw `graph.transition.accepted` cannot mint illegal current state

Validation order in `_validate_accepted_transition`: non-blank types → runtime family → enum membership → declared edge → trigger == edge.trigger → guard_id == edge.guard_id → reduced current state (or `FAMILY_DEFAULT_STATES`) → `evaluate_guard`. Failure raises `GraphEventContractError` on the **input** state; the write happens only after return.

Independent probes (raw `EventStore.append`, no `submit`):

| Case | Outcome |
|---|---|
| `queued → snapshot_locked` | `未声明迁移`; no checkpoint; `GraphExecutor.state()` also raises |
| Wrong trigger on `None → running` | `trigger 不匹配` |
| Empty guard evidence on `queued → collecting` | `守卫重求值拒绝: … missing_evidence:candidate_scope_locked` |
| Legal first hop, then `recovering → scientific_qc` | `当前状态不匹配: expected=collecting got=recovering`; no checkpoint |
| Legal `None → running` with valid guard evidence | `state()["project"]["objL"] == "running"`; replay succeeds |

GT11 additionally covers `guard_id` mismatch, bogus `to_state`, and non-string `from_state` (`test_checkpoint_replay.py` 445–494). Those were not re-probed independently; they are covered by the GREEN GT11 run.

### 3. Raw `graph.node.completed` cannot forge completions

`_validate_node_completed` (`reducer.py` 236–317) checks scope vs contract, A/B/C vs shared, output key set, completion predicate, `validate_typed_outputs`, recomputed `completion_digest`, recomputed `event_id` (`stable_id`), and recomputed idempotency key — same material as `complete_node`.

Independent probes:

| Case | Outcome |
|---|---|
| Legal `resolve` (shared, valid evidence refs) | Ledger gained `frag_1`; replay kept the event id |
| Shared `resolve` + `report_kind="A"` | `resolve 是 shared 节点，不接受 report_kind`; no checkpoint |
| `intake` output `project_contract_id=5` | `intake 输出类型不合法` |
| Drifted `completion_digest` | `completion_digest 不匹配` |
| Drifted `event_id` | `事件 ID 不匹配` |
| Drifted `idempotency_key` | `幂等键 不匹配` |
| `graph.unknown` | `未知图事件类型: graph.unknown` |

### 4. Exact 11-node rerun (this session)

```
.venv/bin/pytest \
  tests/graph/test_transition_matrix.py::test_project_run_transitions_and_guards_match_v12 \
  tests/graph/test_transition_matrix.py::test_report_evidence_transitions_and_guards_match_v12 \
  tests/graph/test_transition_matrix.py::test_artifact_transitions_and_guards_match_v12 \
  tests/graph/test_transition_matrix.py::test_download_request_transitions_and_guards_match_v12 \
  tests/graph/test_transition_matrix.py::test_revision_approval_transitions_and_guards_match_v12 \
  tests/graph/test_transition_matrix.py::test_every_undeclared_transition_is_rejected_and_logged \
  tests/graph/test_graph_node_contracts.py::test_intake_preflight_universe_and_route_nodes_declare_complete_contracts \
  tests/graph/test_graph_node_contracts.py::test_ingest_extract_resolve_and_gate_nodes_declare_complete_contracts \
  tests/graph/test_graph_node_contracts.py::test_snapshot_analysis_format_and_acceptance_nodes_declare_complete_contracts \
  tests/graph/test_graph_node_contracts.py::test_report_branches_share_evidence_without_sharing_gate_state \
  tests/graph/test_checkpoint_replay.py::test_replay_never_duplicates_publish_move_approve_or_delete \
  -q --tb=line
```

**Result: 11 passed in 23.43s, exit 0.** This is not inherited from `__pycache__` or a prior cancelled turn.

### Residual issues that are not the old P1s

These remain on the current files. None restore the closed P1s.

- Guards still evaluate **caller-supplied** booleans; they are not derived from live `format_artifact` / selected-object maps. That is structured-guard 3.4, not live product truth (3.5/3.7).
- `typed_inputs` are still unused at `complete_node`; `input_digest` is still an opaque string. Same digest + drifted outputs fail closed (GT08 + reducer digest check). Different digest for the same logical inputs still creates a new completion.
- Combined GT11 crash still fires after the **first** of the four-op stream (publish). Path-only delete was independently crashed this round; move/approve were not independently crashed.
- Raw **accepted** events re-check edge/trigger/guard/current state, but unlike node completion they do **not** re-derive `event_id` / `idempotency_key`. A legal transition with a forged id still applies once; a second illegal hop then fails current-state. Weaker than the node path, not a matrix bypass.
- Side-effect payloads that have a valid target but lack `source_path` still reach `_publish` and can `KeyError` after the reducer has updated in-memory `side_effects`. Checkpoint is not saved. Fail-closed, but the error type is not `SideEffectTargetError`.

§10.1 node sequencing and emitting publish/move from `complete_node` remain Task 3.5. They are not re-scored as 3.4 P1.

## Evidence And Assumptions

### Evidence

- `reducer.py` 87–125, 157–353: shared target derivation; accepted/completed contract checks; unknown `graph.*` → `GraphEventContractError`.
- `executor.py` 23, 192–263: all four side-effect ops call `derive_side_effect_target`.
- `test_checkpoint_replay.py` 220–531 and 533+: path-only delete, malformed targets, raw accepted forgeries, legal raw accepted, raw completed forgeries.
- Pytest: `11 passed in 23.43s`.
- Probe: 23/23 PASS under `/tmp/ci_t34_r4_uf5j211y`, including crash-after-delete-before-checkpoint for path-only delete.

### Assumptions

- Task 3.5 still owns §10.1 walk and wiring node completion to the four side-effect event types.
- Task 3.7 still owns binding `isolated_qc_accepted` / `qc_verdict` to a real verifier.
- Caller-supplied guard flags remain the 3.4 contract unless Codex reopens live-state binding.

### Inference

- On **current** files, the control graph is no longer “submit-only enforcement plus a trusting fold.” Reduce-time checks close the shared-EventStore forgery path for accepted transitions and node completions.
- Path-only delete is a supported, replayable shape. The old reducer/executor split is gone.
- Remaining gaps are residual 3.4 hygiene or 3.5/3.7 handoff, not reopenings of the two P1s.

### Uncertainty

- Move and approve were not independently crashed in `/tmp` (only delete path-only + the GT11 publish-first combined stream).
- `guard_id` mismatch and bogus `to_state` were verified via GREEN GT11, not a second independent script.
- Full-repo pytest / Ruff / mypy / wheel were not in this role’s assignment and were not run.

## Risks, Gaps, And Verification Needs

### Closed (do not keep as open P1)

1. Delete target-identity split — closed by `derive_side_effect_target` + path-only replay probe + GT11.
2. Raw accepted forgery of current state — closed by `_validate_accepted_transition` + probes + GT11.
3. Raw completed forgery of outputs/scope/digest/ids — closed by `_validate_node_completed` + probes.

### Open P0

None observed on current files with the executed suite and probes.

### Open P1

None observed on current files. The two historical P1s are not restated.

### Open P2

1. Guard booleans are still caller assertions, not live selected-object / artifact state.
2. `input_digest` is still caller-chosen; `typed_inputs` are declaration-only.
3. Combined four-op crash window in GT11 still interrupts after publish only; move/approve lack an independent crash probe.
4. Accepted raw events do not re-bind `event_id` / `idempotency_key`; non-target missing fields (`source_path`) can still `KeyError` after in-memory ledger update (checkpoint not persisted).

## Recommended Next Step

Codex can accept Task 3.4 on this evidence if the remaining P2s are filed as 3.5/3.7 or follow-up hygiene. Suggested cheap follow-ups, not blockers: re-derive accepted-event ids like node completion; crash move/approve independently; fail-close missing `source_path` before reducer ledger write. Do not reopen the old P1s against the pre-fix snapshot.

## Verdict

PASS

P0=0; P1=0; P2=4
