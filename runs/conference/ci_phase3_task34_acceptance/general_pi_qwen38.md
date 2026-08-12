All evidence is in. Compiling the independent acceptance report.

# Conference Participant Output: ci_phase3_task34_acceptance - general_pi_qwen38

## Boundary Check

- Read-only inside the workspace: yes. No repo file created/modified. Adversarial probes ran from `/tmp/ci_task34_pi_probes/probe_suite.py` and wrote only to `tempfile` temp dirs; `PYTHONDONTWRITEBYTECODE=1` + `-p no:cacheprovider` suppressed byte-code/cache writes. Interpreter: `.venv/bin/python` = Python 3.13.13, pytest 9.1.1 (system `python3` is Xcode 3.9 and cannot import the suite — environment note, not a code defect).
- Did not read worker reports or the other participant's output; did not touch Task 3.5/3.6/3.7 scope, report portal, or security testing.
- Executed exactly the 11 approved node ids (not directory-level pytest) — all names verified in the verbose transcript: `11 passed in 23.11s`.
- Bounded regression I additionally ran (Codex still owns full-repo pytest/Ruff/mypy/wheel/diff): `tests/graph tests/unit/test_state_enums.py tests/integration` → `205 passed in 30.43s`.

## Independent Work Product

### 1. Approved nodes — exact execution result

All 11 nodes PASSED (`artifact://6`): GT01–GT05 transition-matrix freezes, GT06 undeclared-Cartesian rejection, GT07–GT09 node-contract groups, GT10 branch isolation, GT11 replay idempotency.

### 2. Literal-fixture vs v1.2 §10.2 manual diff (not derived from production)

I diffed the test literals against the spec table (`docs/specs/...-v1.2.md:312-345`) edge by edge:

- **GT01 project** (`tests/graph/test_transition_matrix.py:32-127`): create edge `None→running`, `running↔awaiting_user`, `running→partially_delivered→partial_delivery_blocked`, and "任一未完成态→blocked/complete" expanded as fixed source sets `{running, awaiting_user, partially_delivered}` — no wildcard, per context line 27. Matches v1.2 rows 316-323 exactly (missing=0 extra=0 enforced at test:759-761).
- **GT02 report_evidence** (test:168-260): `queued→collecting→recovering`; `collecting/recovering→scientific_qc`; `scientific_qc→snapshot_locked` only via `isolated_qc_accepted` with contradiction pair vs `qc_veto`; fixable veto only `→recovering`; unfixable+exhausted `→evidence_blocked`; `snapshot_locked→superseded`. Matches spec rows 324-329 and context lines 28.
- **GT03 format** (test:324-381): chain `queued→generating→quality_check→passed→delivery_ready`, independent `generating/quality_check→blocked→queued`, `delivery_ready→superseded`. Matches row 330-332.
- **GT04 download** (test:412-491): 11 edges; drift check `graph_pairs == task33_pairs` (test:898-903) against `manual_inbox._DECLARED_TRANSITIONS` (`src/ci_workflow/ingestion/manual_inbox.py:46-69`) — I verified the Task 3.3 frozenset literally contains the same 11 pairs incl. the 3.3-accepted `awaiting_user→needs_re_download` scan edge. `accepted→*` is terminal (test:905). Zero drift.
- **GT05 revision** (test:560-617): validation dispositions, `needs_evidence→submitted`, owner-decision edges, `approved→published` with `approval_id` required field; validation guard ≠ approval guard (test:926) — verification cannot approve.
- Guard bodies are declarative `GuardSpec` literals (`src/ci_workflow/graph/guards.py:75-453`); evaluation order fixed (scope → fields → required_true → required_any → contradictions, guards.py:35-71); empty evidence must fail with `missing_evidence:` prefix for all 43 guards (test:766-770), every true-key flip rejects, contradiction pairs reject. No `allowed=True` bypass exists: registry construction rejects orphaned/mismatched guards (`registry.py:34-55`), and evidence families with any edge fail construction (`registry.py:47-50`).

### 3. Canonical current-state & trigger truth (my probes, not the suite)

- **Probe B** — after `queued→collecting→scientific_qc` on one object, re-submitting the stale `queued→collecting` and `collecting→scientific_qc` requests each yields `graph.transition.rejected` with `reason=current_state_mismatch` and correct `expected_state`; final state stays `scientific_qc`. Enforcement order in `executor.py:340-407`: undeclared → trigger → canonical state → guard; `_canonical_current_state` (executor.py:425-431) reduces the real event stream, never trusts the request.
- **GT06 substance re-verified by reading the full body** (test:1051-1162): complete Cartesian products over all nine families including `from_state=None`, fresh objects positioned via literal-fixture BFS only (test:719-732 — no production traversal), same-state pairs rejected, cross-family foreign `to_state` rejected, evidence families rejected for every attempt including `None` sources. Trigger/run/project mismatches produce typed rejection events carrying `expected_*` fields (executor.py:466-518). Replay of identical request returns the stored event with zero new appends; same identity + drifted payload raises `EventConflictError` (test:1301-1317; my probe G confirmed the same for node completions).

### 4. Identity (project/run/request/node)

- Project root anchors one project: foreign-project `submit` → rejection event stamped with the *established* project (executor.py:314-325, GT06 test:1280-1299); foreign-project `complete_node` fails before write (executor.py:547-552, GT08 test:309-318); multi-project store → `ValueError` (executor.py:409-416).
- Run identity: my **probe A** — two executors, same root, `run_alpha`/`run_beta`, same object `report_A`: states evolve independently (`alpha=collecting`, `beta=scientific_qc`); a foreign-run attempt is audited *under the executor's run* (`run_mismatch`, event.run_id == executor run) and does not pollute the requested run's state.
- Node completion identity = project+run+node+report-or-shared+input_digest (`executor.py:569-576`). My **probe G**: same `input_digest` for `gate` A vs B → distinct events and isolated `gate.A/gate.B` state; same identity with drifted outputs → `EventConflictError`; shared-scope node rejects `report_kind`.

### 5. A/B/C isolation & shared EventStore coexistence

- `initial_state()` materializes 12 report-scoped keys, no shared `gate/snapshot/analysis/artifact` key (`state.py:62-70`; GT09/GT10 mechanical assertions, test_graph_node_contracts.py:369-382, 502-541). GT10 drives the whole scenario through real declared paths; A blocked leaves B's gate/snapshot untouched (test:582-587).
- Coexistence: reducer no-ops non-graph business events but keeps them in lineage (`reducer.py:96-100`); GT11 and my **probe E** use the *real* Task 3.3 event type `download_request_state_changed` (manual_inbox.py:703) — preserved in `applied_event_ids` and stream digest. Unknown `graph.*` fail-closed on both `replay` (GT11 test:188-211) and `executor.state()` (my **probe H**).

### 6. Crash window & checkpoint recovery

- **GT11**: crash after first effect → recovery replay executes publish/move/approve/delete exactly once each; ledger=4; approvals=1; re-replay returns identical checkpoint; drifted payload same key → `EventConflictError`.
- My **probe E** (stronger crash point): crash after the *move* (4th of 6 events, mid-stream, with a transition + foreign event interleaved): partial state exactly `{published, moved}` only, no checkpoint; recovery converges all four classes once-each, foreign event in lineage, `last_sequence=6`; appending a new event after checkpoint resumes incrementally with zero side-effect re-runs (ledger stays 4). Resume path verified, not just cold replay.

## Evidence And Assumptions

**Evidence (directly observed):**

1. Exact 11-node run: `11 passed in 23.11s` (verbose list confirms each approved id; rootdir config `pyproject.toml`, Python 3.13.13).
2. Regression set: `tests/graph tests/unit/test_state_enums.py tests/integration` → `205 passed in 30.43s`.
3. Probe suite (`/tmp/ci_task34_pi_probes/probe_suite.py`, output above): A/A/B/C2/E/E/G/H PASS; C1 OBSERVED; **D DEFECT**.
4. **Defect D — delete target-identity asymmetry (P1).** `IdempotentSideEffects._delete` derives `target_identity = payload.get("target_identity", payload["path"])` (`executor.py:256`), but the reducer's `_side_effect_target` falls back to `payload["approval_id"]` (`reducer.py:81-86`). For an `artifact.delete` event without `target_identity` — a shape nothing forbids, since payloads are free-form dicts — `graph_reducer` raises untyped `KeyError('approval_id')` during replay/state. Since `CheckpointStore.replay` runs the reducer *before* the effect (`checkpoint_store.py:202-204`), such a stream can never checkpoint again and the delete never executes; `executor.state()` on that stream is also dead. The reducer docstring itself claims "与 IdempotentSideEffects 一致" — that invariant is false for this shape. GT11 stays green only because its fixture delete payload includes `target_identity`; the requirement is enforced nowhere.
5. Probe C1 observation (P2, trust model): a raw `store.append` of a well-formed `graph.transition.accepted` for an undeclared edge reduces to state (`snapshot_locked` in my probe). All v1.2 enforcement lives at the `submit()` boundary; the event log is the trust anchor (EventStore already accepts arbitrary well-formed foreign events by design for Task 3.1–3.3 coexistence). The reducer *does* fail-close for evidence-family accepted events (probe C2), unknown `graph.*`, and EventStore rejects identity/payload drift — but it does not re-check declared edges/guards.

**Assumptions:**
- The approved plan's GT contract as transcribed in `context/ci_phase3_task34_context.md` is authoritative (plan original is outside workspace and not authorized for me).
- `artifact.delete` payloads with `target_identity` are the contract shape (per GT11 fixture and reducer docstring); the defect is the unenforced, divergent fallback — not that GT11's scenario is wrong.
- Performance of per-submit full-stream re-read (`executor.py:411,420,427` → O(n²) over a run) is acceptable at local per-project scale; noted P2 only.

## Risks, Gaps, And Verification Needs

- **P1 (blocks acceptance under the stated rule):** Defect D above. Remediation (small, in-scope): extract one shared `side_effect_target(event)` derivation used by both `reducer.py` and `executor.py` (per-op fallbacks: approve→`approval_id`; publish/move→`target_identity`; delete→`target_identity` else `path`), and validate side-effect payload shape at reduce time raising `SideEffectError`/`CheckpointIntegrityError` instead of `KeyError`. Add one tmp-dir regression node covering a `target_identity`-less delete event through crash-window replay.
- **P2-1:** Reducer trust boundary — document that `graph.transition.accepted` payloads are trusted post-append (event-log trust model), or add defense-in-depth edge/guard re-validation in `graph_reducer`. I recommend documenting, not re-validating: re-validation couples replay to the *current* registry version and can break legitimate historical replay after a future contract version bump.
- **P2-2:** O(n²) stream re-read per `submit`/`complete_node`; fine for 3.4, flag for Task 3.5 orchestration scale.
- Verification needs for Codex: full-repo pytest/Ruff/strict mypy/wheel/diff (checklist items Codex owns); after D fix, re-run GT11 plus the new delete-shape node in this same Pi session.

## Recommended Next Step

Codex decides one bounded question: **fix Defect D as a Task 3.4 closure patch (single shared target-identity helper + typed fail-closed validation + one crash-window regression node), or reclassify to P2 with a mandatory pre-3.5 gate?** My recommendation: fix now — the defect sits exactly in the crash-window recovery path Task 3.4 exists to protect, the fix is ~15 lines across two Task 3.4 files, and Task 3.5 will immediately consume `replay()` with orchestrator-emitted side-effect payloads. Safe provisional path if deferred: no producer emits side-effect events yet, so nothing is at risk until 3.5 — but gate 3.5 start on the fix. After the patch, re-dispatch to this session for targeted re-verification (GT11 + probe D rerun).

## Verdict

FAIL — the artifact is a genuinely typed, deterministic, replayable control graph in every probed dimension except one internal contract inconsistency in the delete side-effect recovery path; none of the 11 approved nodes is a false green, but the stated acceptance rule (any P1 ⇒ FAIL) applies.

`P0=0; P1=1; P2=2`
