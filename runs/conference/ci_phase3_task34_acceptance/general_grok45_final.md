# Conference Participant Output: ci_phase3_task34_acceptance - general_grok45

## Boundary Check

- Role `general_grok45` / Grok Build `grok-4.6` in session `8d0d63cd-72a0-421c-af9f-1f77c9ac4356`. This is the final same-session completion after two cancelled turns. No new session, no restart.
- Workspace only: `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`. No production paths outside the packet. No Hermes provider semantics. `SOUL.md` was not read.
- Read-only. No source, test, context, plan, Trellis, or report files were written or edited. This report is returned in-band only; `runs/conference/ci_phase3_task34_acceptance/general_grok45_final.md` was not created by tools.
- Pi participant output and worker reports were not read.
- Visual / PPT / browser / current-web / clinical-regulatory acceptance was not performed. Codex remains final authority.
- Tools: first turn read the assigned packet and implementation. Both later pytest/probe commands were cancelled before producing output. No additional tool calls in this turn.

**Read this session (complete):**

| Path | Use |
|---|---|
| `AGENTS.md` | Project rules |
| `context/ci_phase3_task34_acceptance_conference_context.md` | Conference SoT, GT scope |
| `context/ci_phase3_task34_context.md` | GT01–GT11 fixed contract |
| `plans/codex_main_venue_ci_phase3_task34_acceptance.md` | 11 exact node ids |
| `docs/specs/competitive-intelligence-workflow-design-v1.2.md` §5.3, §10.1–10.2 | Product matrix and graph constraints |
| `src/ci_workflow/domain/enums.py` | Nine state families |
| `src/ci_workflow/domain/ids.py` | `stable_id` |
| `src/ci_workflow/storage/event_store.py` | Shared append-only identity |
| `src/ci_workflow/storage/checkpoint_store.py` | Replay / crash window |
| `src/ci_workflow/ingestion/manual_inbox.py` `_DECLARED_TRANSITIONS` | Task 3.3 download pairs |
| `src/ci_workflow/graph/{__init__,types,state,transitions,guards,registry,reducer,executor}.py` | Production graph |
| `src/ci_workflow/graph/definitions/{__init__,new_report.py}` | 14 node contracts |
| `tests/graph/test_{transition_matrix,graph_node_contracts,checkpoint_replay}.py` | GT01–GT11 |

**Not executed this session (unverified, not omitted):**

- The 11 exact pytest nodes (command cancelled twice).
- Temp-dir probes for path-only `artifact.delete`, input/output drift at runtime, EventStore state forgery, unknown `graph.*` replay, and four independent crash windows.

`tests/graph/__pycache__/` contained `cpython-313-pytest-9.1.1` artifacts from some earlier process. That is not this session’s result and is not treated as acceptance.

## Independent Work Product

### Audit of the objective

Task 3.4 is accepted only if the artifact is a typed, deterministic, replayable control graph: literal v1.2 matrix with `missing=0 extra=0`, real current-state enforcement, trigger/guard truth, project/run/request/node identity, `input_digest` fail-closed drift, typed outputs, A/B/C isolation, shared EventStore coexistence, unknown `graph.*` fail-closed, and publish/move/approve/delete crash-window idempotency. A green table-plus-test collection is not enough. Defects that belong to 3.4 must not be deferred to 3.5/3.6/3.7.

### What the production graph actually is

Two parallel subsystems, not one executed §10.1 graph:

1. A frozen transition registry + `GraphExecutor.submit()` that writes `graph.transition.accepted|rejected`.
2. A node-contract registry + `GraphExecutor.complete_node()` that writes `graph.node.completed`.

`graph_reducer` folds those events (plus four side-effect types) into `initial_state()`. `GraphExecutor.replay()` delegates to `CheckpointStore.replay`. There is no node DAG, no runner that walks §10.1, and no path from `complete_node` to `artifact.publish` / `artifact.move` / `revision.approve` / `artifact.delete`. GT11 injects those four events directly into `EventStore`.

That split is compatible with Task 3.5 owning orchestration, **if** the 3.4 body (matrix, submit enforcement, reducer, side-effect protocol) is internally consistent. Two places are not.

### Highest-impact defect: delete identity is not one contract

`IdempotentSideEffects._delete` and `graph_reducer` do not agree on the delete payload.

```254:263:src/ci_workflow/graph/executor.py
    def _delete(self, event: StoredWorkflowEvent) -> None:
        payload = event.payload
        target_identity = str(payload.get("target_identity", payload["path"]))
        digest = _payload_digest(payload)
        if self._guard_ledger(event=event, target_identity=target_identity, payload_digest=digest):
            return
        path = self._relative(str(payload["path"]))
        if path.exists():
            path.unlink()
        self._record(event=event, target_identity=target_identity, payload_digest=digest)
```

```81:86:src/ci_workflow/graph/reducer.py
def _side_effect_target(payload: dict[str, Any]) -> str:
    """与 IdempotentSideEffects 一致的目标身份：approve 用 approval_id。"""
    target = payload.get("target_identity")
    if target is None:
        target = payload["approval_id"]
    return str(target)
```

`CheckpointStore.replay` applies **reducer first, then** the side effect (`checkpoint_store.py` 199–206). A legal-looking `artifact.delete` with `path` and no `target_identity` therefore hits `payload["approval_id"]` and raises `KeyError` **before** delete runs. Replay cannot converge. The comment claiming consistency with `IdempotentSideEffects` is false for this shape.

GT11 never exercises that shape. It always supplies both keys:

```92:96:tests/graph/test_checkpoint_replay.py
            event_type="artifact.delete",
            idempotency_key="delete:obsolete",
            payload={"target_identity": "staging/obsolete.json", "path": "staging/obsolete.json"},
```

If `target_identity` is missing and `approval_id` is present by mistake, the reducer would ledger under the approval id while `_delete` ledgers under `path` — split identity on the same event.

**Classification:** P1. This is Task 3.4’s own crash-window protocol, not 3.5 orchestration. GT11 is green-shaped coverage, not proof that delete replay is closed.

**Remediation:** One fallback, used by both reducer and `_delete`: `target_identity` required, or fallback `path` for `artifact.delete` and `approval_id` only for `revision.approve`. Add a GT11-class case: delete payload `{path}` only; crash after reducer-or-effect; replay once; ledger key stable.

### Second P1: accepted events are trusted at reduce time

`submit()` does enforce declared edge, trigger, and canonical current state (`executor.py` 340–379). `graph_reducer` does not:

```102:108:src/ci_workflow/graph/reducer.py
    if event.event_type == "graph.transition.accepted":
        family = str(event.payload["family"])
        if family not in RUNTIME_STATE_FAMILIES:
            raise ValueError(f"证据状态族不接受迁移事件: {family}")
        family_state = dict(result.get(family, {}))
        family_state[str(event.payload["object_id"])] = event.payload["to_state"]
        result[family] = family_state
```

Any shared-store writer can `EventStore.append` a `graph.transition.accepted` that jumps `queued → snapshot_locked` or forges `project → complete`. Replay will install that state. Unknown `graph.*` is fail-closed (96–98); **known** graph events are not re-validated. Task 3.4 explicitly requires coexistence on the same EventStore and “不能乱序/伪造当前状态.” Enforcement that lives only in `submit()` is not the control graph; it is an API wrapper around a trusting fold.

GT06 / GT10 only go through `submit()`. That cannot see this hole.

**Remediation:** In `graph_reducer`, reject unless `(family, from_state, to_state)` is declared, `from_state` equals the reduced current state (or the typed default), and `to_state` is a member of that family. Same unknown-event posture as `graph.unknown`.

### What does hold, by inspection (runtime unverified)

**Matrix and fixtures.** GT01–GT05 are literal `LiteralEdge` fixtures in `test_transition_matrix.py`, not reverse-generated from `TRANSITION_REGISTRY`. Production `transitions.py` matches those fixtures line-for-line, including:

- project `None → running`; incomplete set `{running, awaiting_user, partially_delivered}` expanded to `blocked` / `complete`; `blocked` / `partial_delivery_blocked → running`
- report: QC accept → `snapshot_locked`; fixable veto → `recovering` only; unfixable exhausted → `evidence_blocked`; `snapshot_locked → superseded`
- format chain `queued → generating → quality_check → passed → delivery_ready`; independent block/reopen; `delivery_ready → superseded`
- download pairs equal Task 3.3 `_DECLARED_TRANSITIONS` (`manual_inbox.py` 46–69), including the extra `awaiting_user → needs_re_download` allowed by v1.2 “至少遵循”
- revision: validation ≠ owner approval; publish requires `approval_id`

Registry construction rejects duplicate edges, missing guards, orphan guards, and any edge on the four evidence families (`registry.py` 34–55).

**Current-state / trigger / identity at `submit()`.** Order is: exact replay → project identity → run identity → undeclared → trigger → `_canonical_current_state` → guard (`executor.py` 285–407). Unseen objects use `FAMILY_DEFAULT_STATES` (`state.py` 37–43). Cross-project writes rejection events still stored under the established `project_id`. Cross-run writes rejection under the executor `run_id`. Same `request_id` + same digest returns the existing event; digest mismatch raises `EventConflictError`.

**Guards.** `evaluate_spec` is deterministic (`missing_evidence` / `guard_not_satisfied` / `contradictory_evidence` / `scope_mismatch`). Empty evidence cannot pass. Required-true uses `is True`. This is real structured evaluation of a **caller-supplied** dict, not derivation from live artifact/report maps.

**Node contracts.** 14 nodes, `missing=0 extra=0` against the GT07 list. Frozen dataclass; typed outputs have a closed vocabulary in `validate_typed_outputs` (`types.py` 131–181). `complete_node` requires exact output names, predicate, type check; shared nodes reject `report_kind`; report/artifact nodes require A/B/C; empty `input_digest` fails. Identity is `project_id + run_id + node_id + report-or-shared + input_digest`. Same digest + different `completion_digest` is `EventConflictError`. Different runs keep distinct event ids. Later `occurred_at` is ignored for completion identity.

**A/B/C.** `initial_state()` has no shared `gate`/`snapshot`/`analysis`/`artifact` keys; 12 `family.kind` slots (`state.py` 62–70). `resolve` writes the shared evidence ledger; `gate`/`snapshot`/`analyze`/`format` write report-scoped keys. One report’s `report_evidence` transition cannot overwrite another object’s slot **if both go through `submit()`**.

**Unknown `graph.*` and foreign events (code only).** `GRAPH_EVENT_TYPES` is the three graph types plus the four side-effect types (`reducer.py` 16–28). `graph.unknown` raises. Non-graph, non-side-effect types return a shallow copy (no-op) and remain in the event stream / checkpoint `applied_event_ids` if replay succeeds. GT11 writes this test; this session did not run it.

**Crash window for the GT11 shape (code only).** Ledger key is `(op, idempotency_key, target_identity)`. Publish/move inspect destination+source digests; approve compares `decision`; delete unlinks if present. Checkpoint is saved only after the full new-event loop. GT11 crashes after the first successful side effect (publish) and replays the same `IdempotentSideEffects` instance. Move/approve/delete are not independently crashed. Path-only delete is untested (see P1).

### Adversarial cases requested — status

| Probe | Result this session |
|---|---|
| 11 exact nodes | **Unverified** (pytest cancelled) |
| `artifact.delete` with `path` only, no `target_identity` | **Not executed.** Code-level contradiction is enough to file P1 |
| Node completion input/output drift | **Not executed.** Code + GT08 intend: same digest + drifted outputs → `EventConflictError`; typed_inputs never hashed |
| State forgery via raw `graph.transition.accepted` | **Not executed.** Reducer will apply `to_state` with no matrix check → P1 |
| Unknown `graph.*` | **Not executed.** Reducer raises `未知图事件类型` if replay reaches it |
| Four independent crash windows | **Not executed.** Only publish-first crash exists in GT11 |

## Evidence And Assumptions

### Evidence (observed)

- v1.2 §10.2 table and “任何未声明迁移均拒绝并写入事件日志”; §5.3 typed node fields + independent accept/veto; §10.1 fourteen-step new-report procedure.
- Production files and line ranges cited above.
- GT01–GT05 fixtures are hand-written; `_assert_family_frozen` compares fixture set to `declared_edges` and prints `missing=… extra=…`.
- GT06 cartesian uses production `declared()` only to choose accept vs reject after fixtures already froze the matrix; positioning walks **fixture** BFS, not the production table.
- `IdempotentSideEffects.__call__` ignores unknown `event_type`; only the four names run effects (`executor.py` 134–143).
- `_established_project` uses **all** store events, not graph events only (`executor.py` 409–416). One foreign Task 3.3 event is enough to pin `project_id`.
- `request_digest` is SHA-256 of `TransitionRequest.model_dump(mode="json")`, which includes `occurred_at` and `actor_id` (`executor.py` 294, `types.py` 39–59).
- `completion_digest` is `{node_id, report_kind, input_digest, outputs}` only (`executor.py` 561–567).
- Completion predicate is `all(outputs.get(field) is not None)` (`definitions/new_report.py` 23–28), not non-emptiness.
- Guard scope keys are checked only if present (`guards.py` 36–43).
- `tests/graph/__pycache__/*.pyc` exist; no pass/fail output was captured here.

### Assumptions

- Task 3.5 may own §10.1 sequencing and wiring node completion to the four side-effect event types. Missing DAG is not scored as 3.4 P0/P1.
- Task 3.7 may own binding `isolated_qc_accepted` / `qc_verdict` to a real verifier. Open-string `qc_verdict` is P2.
- Caller-supplied guard booleans are the 3.4 contract (“结构化守卫求值”), not live derivation from `format_artifact` maps. That residual is P2, not a silent pass of “actual guard truth” in the product sense.
- `EventStore` writers other than `GraphExecutor` are in-scope for coexistence (conference text). If Codex rules they are trusted, P1-2 drops to P2.

### Inference (not evidence)

- The artifact is a real typed **registry** and a real **submit-time** state machine, plus a default fold/replay loop. It is not yet a single control graph that cannot be forged on the shared log, and the delete half of the advertised idempotent protocol is not closed.
- GT11 can be green while path-only delete replay is broken. That is the false-green pattern this acceptance was told to look for.
- `running → complete` with asserted flags and zero artifacts is allowed by 3.4 code. That is consistent with “evaluate supplied evidence,” inconsistent with a reviewer reading v1.2 guards as live conditions.
- Transition retries that rebuild `occurred_at=now()` under the same `request_id` will `EventConflict`, unlike `complete_node`. Crash recovery that does not persist the original `TransitionRequest` will fail closed the wrong way.

### Uncertainty

- Whether the 11 nodes are currently GREEN in this tree.
- Whether an in-process probe of path-only delete raises `KeyError` exactly as the source implies (no runtime confirmation).
- Whether interleaved multi-run `CheckpointStore` prefix checks (`read_all()[:last_sequence]` then filter `run_id`, `checkpoint_store.py` 188–194) hold; inspection looks consistent with global sequences, untested here.
- Whether Codex treats reducer defense-in-depth as 3.4-required.

## Risks, Gaps, And Verification Needs

### P1 (fail)

1. **Delete target identity split** — `executor.py` 256 vs `reducer.py` 81–86 vs `checkpoint_store.py` 202–204. Path-only `artifact.delete` cannot replay. GT11 hides it.
2. **Reducer trusts `graph.transition.accepted`** — `reducer.py` 102–108. Shared EventStore can mint illegal current state. `submit()` cannot compensate.

### P2 (do not defer if cheap; not 3.4 blockers by themselves)

1. Guards are caller flags, not live selected-object / artifact state. `partially_delivered → blocked` plus `no_deliverable_artifact=True` is a spec-shaped contradiction the matrix still allows.
2. `typed_inputs` are unused at `complete_node`; `input_digest` is an opaque string. Same logical inputs with a new digest duplicate; true input hashing is not in 3.4.
3. No §10.1 order; `side_effect_class` on `format`/`acceptance` does not emit publish/move events.
4. GT11 crashes only after publish; move/approve/delete inner windows and path-only delete are uncovered.
5. `target_family` / `target_object_id` are optional, so cross-object evidence passes if omitted.
6. NodeContract omits v1.2 §5.3 timeout, cost, and explicit preconditions; `scientific_qc` can self-complete via `complete_node`.
7. Coexistence leftovers: graph download family vs `ManualInboxService` can drift at runtime; `project` family is a multi-`object_id` map (no singleton run state); transition digest includes clock/actor.

### Most important objections

- “Tests are the contract” is false for delete and for reduce-time forgery. Both are 3.4 body.
- “3.5 will bind guards and emit side effects” does not repair a reducer that KeyErrors on the delete shape `_delete` itself implements.
- “Unknown graph events are fail-closed” is incomplete while known accepted events are unchecked.

### Proposed solutions

1. Unify delete/approve target extraction; add path-only delete to the replay suite; crash each of the four ops once.
2. Re-validate declared edge + current state inside `graph_reducer` (and optionally refuse non-executor `graph.transition.*` if an actor/provenance field is added).
3. If Codex wants live guard truth in 3.4, derive the boolean keys from reduced family maps; otherwise record an explicit 3.5 handoff so reviewers stop treating asserted flags as product truth.
4. Codex must re-run the 11 nodes locally; this session cannot claim GREEN.

### Decision points for Codex

1. Is path-only `artifact.delete` a supported 3.4 payload? If yes, P1-1 is mandatory. If no, `_delete`’s fallback must be removed and the payload schema closed.
2. Are non-executor `EventStore.append` of `graph.transition.accepted` in-scope? If yes, P1-2 is mandatory. If no, document the trust boundary and drop to P2.
3. Are live-state guards 3.4 or 3.5? This report scored them P2.

### Bounded questions

1. Confirm the canonical delete payload: required `target_identity`, or `path` as identity.
2. Confirm whether reducer-level matrix checks are required before 3.4 acceptance.
3. After any fix, re-dispatch this same session with pytest output and a path-only delete probe; do not treat `__pycache__` as evidence.

## Recommended Next Step

Treat Task 3.4 as **not acceptable**. Codex should (1) locally run the 11 named nodes, (2) require a reducer/side-effect identity fix and a reduce-time matrix check before any PASS, (3) keep 3.5/3.6/3.7 from absorbing P1-1 and P1-2, (4) re-verify in this session rather than a new one. Safe provisional path until those two P1s are closed: do not archive or commit 3.4 as accepted.

## Verdict

FAIL

P0=0; P1=2; P2=7
