I'll start with an independent audit of the Task 3.5 contract, then read the assigned sources and run the two test nodes before any verdict.Next I’ll load the Task 3.5 context, the v1.2 contract sections, and the graph/recovery implementation so the attack plan is grounded.The coordinator is large; I’ll finish the remaining implementation, the v1.2 contract sections, and the two scenario tests next.The tests look broad; I’ll finish the blocked-test tail and inspect guards/executor next so the probes can target contract holes, not just the happy path.Official tests and an independent `/tmp` probe will run next; the probe targets the simultaneous-delivery-and-exhaustion path the suite never hits.The system Python 3.9 can’t collect the suite (`datetime.UTC`). I’ll switch to the project interpreter and rerun the same two nodes.Official nodes are green. I’ll now run system-temp probes against the production coordinator, including the simultaneous-delivery-and-exhaustion path the suite never covers.P6/P6b look like a real deadlock: delivery plus exhaustion from `running` never reaches `partial_delivery_blocked`. I’ll confirm recovery is impossible and rerun a clean two-cycle probe.Deadlock is confirmed. I’ll check whether Task 3.4 already recorded this as a known gap, then finish the awaiting_user case.# Conference Participant Output: ci_phase3_task35_acceptance - general_grok45

## Boundary Check

- Role: `general_grok45` / Grok Build / `grok-4.6`. No Hermes provider semantics. `SOUL.md` was not read.
- Workspace only: `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`.
- Read-only. No source edits. No production-path writes. Report file not written by this agent; runner persists this response.
- Other participant / worker / Codex review outputs were not read.
- Visual / browser / PDF / PPT / clinical-regulatory acceptance not claimed. Codex remains final authority.
- Additional reads beyond the initial set, with reason:
  - `.trellis` session/phase context (session start).
  - `src/ci_workflow/graph/__init__.py` (whether recovery is exported).
  - `src/ci_workflow/graph/guards.py` aggregate guard keys.
  - `src/ci_workflow/graph/transitions.py` project edges.
  - `src/ci_workflow/graph/reducer.py` non-graph no-op path.
  - `src/ci_workflow/graph/executor.py` `submit` / `state`.
  - `context/ci_phase3_task34_acceptance_2026-08-13.md` (Task 3.5 context lists it as the accepted 3.4 boundary).
  - `.trellis/tasks/08-12-phase-3-evidence-gates-recovery/{prd.md,implement.md,task.json}` (Task 3.5 wording).
- Tools used: filesystem reads, ripgrep, project venv pytest, system-temp Python probes under `/var/folders/.../ci_t35_probe_*` and `/tmp/ci_t35_probe*.py`. Nothing written into the repo.

## Independent Work Product

### Independent audit (before probes)

**Objective.** Task 3.5 must make selection immutable after the first public action, keep report/format objects independent, distinguish `blocked` / `partially_delivered` / `partial_delivery_blocked` / `complete`, recover from repeated blocks via epoch-scoped reopen, rebind report versions only to a qualifying reopen, and fail-close forged coordinator events on the shared EventStore read path.

**Source of truth.** v1.2 §10.2 prose plus the declared 3.4 table; `recovery.py` as the only new orchestrator; official nodes `tests/graph/test_partial_delivery.py` and `tests/graph/test_partial_delivery_blocked.py`.

**Highest-impact uncertainty going in.** The frozen table has `running → partially_delivered` only when something is still continuable, and `partial_delivery_blocked` only from `partially_delivered`. There is no `running → partial_delivery_blocked`. If first delivery and remaining exhaustion land in the same reconcile from `running`, the coordinator can compute the right booleans and still have no legal edge. Official tests never do that: they always leave C (or a reopened format) continuable before the first delivery reconcile.

That assumption is not in the 3.5 success criteria and is not how a real A+PPTX or A-delivered/B-blocked run is ordered.

### Official nodes

Interpreter: `.venv/bin/python` (CPython 3.13). Bare `python3` is macOS 3.9 and cannot collect these files (`datetime.UTC`). That is a runner-environment fact, not a product defect.

```
.venv/bin/python -m pytest tests/graph/test_partial_delivery.py tests/graph/test_partial_delivery_blocked.py -q --tb=short
..  2 passed in 0.20s
```

Both nodes are green. They are not sufficient acceptance. They encode the two-step ordering (delivery while a sibling is still continuable, then exhaust).

### System-temp probes (production coordinator + GraphExecutor)

Probe roots: `/var/folders/yb/31r9763x6_54mdxswxk36c4w0000gn/T/ci_t35_probe_bnhjzo4m` and `ci_t35_p2_5ai93w95`.

| Attack | Result |
|---|---|
| First reconcile, no transition, then same-version drop PPTX | Bind persisted; reducer no-op; `ContractDriftError`. Hold. |
| Duplicate formats / reports / unsorted / `html` as optional / `"banana"` / `0` / `True` / empty reports | 8/8 constructors rejected. Hold. |
| v2 bind, then v2 different selection; then v1; then v2 same-selection replay | Drift fail-close; lower-after-higher fail-close; replay no-append. Hold. |
| HTML in `passed`, not `delivery_ready` | Stays `running`; `all_selected_html_delivery_ready=False`. Hold. |
| A HTML+PDF ready, PPTX blocked | Does **not** complete. Also does **not** leave `running`. See P0. |
| Same-version drop blocked B after A HTML ready | Reconcile fail-close. Hold. |
| New version drop B after A HTML ready | `complete`. Legal explicit reselection. Observation. |
| `conditions(slim same v1)` after A+B bound, A ready, B blocked | Reports `html=True, opt=True` (would-complete). See P1. |
| A HTML ready + B `evidence_blocked`, first reconcile from `running` | Aggregation correct; **no transition**; stays `running`. See P0. |
| A-only HTML ready + PPTX blocked from `running` | Same stuck `running`. See P0. |
| Two-step: delivery while B/C continuable, then exhaust | `partially_delivered` → `partial_delivery_blocked`; silent reconcile cannot leave. Hold. |
| No delivery, all selected blocked | `blocked`; silent reconcile stays. Hold. |
| A HTML + HTML-PPT delivered; A PPTX blocked; B blocked | Artifacts not revoked. Project stuck `running`. Independence holds; terminal state does not. |
| Two format + two project block/reopen cycles, replay, reason drift (two-step setup) | Replay no-append; reason drift `EventConflictError`. Hold. Official node already covers this. |
| Rebind: no reopen / stale / mismatched reason / wrong kind / object reuse / chain break / legal + replay + reason drift | All required fail-closes hold. Legal replay no-append. Hold. |
| `rebind_report` return `conditions` still lists old object | Stale return value. See P2. Subsequent `conditions()` is correct. |
| One project reopen consumed by both A and B | Allowed (per-kind ledger). Observation. |
| Forged `selection_bound`: digest / event_id / idempotency_key / extra key / duplicate formats | All `CoordinatorEventContractError`. Foreign non-coordinator event ignored. Legal replay no-append. Hold. |
| Forged `report_target_bound`: no receipt / reason / selection digest / event_id / key / receipt digest / reuse / chain / stale | All fail-closed. Legal replay + reducer no-op. Hold. |
| Forged v1 selection appended after v2 bind | `CoordinatorEventContractError`. Hold. |
| Full A HTML+PDF ready | `complete`; second reconcile `already_complete`. Hold. |
| `user_material_accepted` cannot reopen format | `CoordinationError`. Hold. |
| `awaiting_user` + A delivered + B blocked | Same hole: no `awaiting_user → partial_delivery_blocked` / `partially_delivered`; stays `awaiting_user`. Same P0 surface. |

Declared edges inspected via `TRANSITION_REGISTRY.declared`:

- `running → partial_delivery_blocked`: **None**
- `awaiting_user → partial_delivery_blocked`: **None**
- `awaiting_user → partially_delivered`: **None**
- `running → complete|blocked|partially_delivered`: present

### P0 — project deadlock when delivery and remaining exhaustion coincide

**Evidence (not inference).**

Canonical case, system-temp, A+B HTML-only:

- State after objects: `report_A=snapshot_locked`, `report_A:html=delivery_ready`, `report_B=evidence_blocked`.
- `reconcile` returns `submitted=None`, `note=no_candidate`, project remains `running`.
- Computed conditions: `delivered=True`, `continuable=False`, `remaining_selected_exhausted_blocked=True`, `no_running=True`, `no_deliverable=False`, `all_selected_html=False`.
- Event tail: last write is `coordinator.selection_bound` only. No `graph.transition.accepted` project move.
- `reopen_project(...)` → `CoordinationError: 项目当前状态 running 不可重新打开`.
- `rebind_report(B → B_v2)` → `CoordinationError` (no qualifying project reopen).
- Second `reconcile` still `no_candidate` / `running`.

Same stuck `running` for:

- A-only + HTML ready + PPTX blocked.
- A HTML+PDF ready + PPTX blocked.
- A HTML+HTML-PPT ready + PPTX blocked + B blocked.
- `awaiting_user` + A HTML ready + B blocked.

**Inference.** The coordinator’s classification matches v1.2 §10.2. The 3.4 table has no edge that can express “already delivered, remainder exhausted” from `running` or `awaiting_user`. Official GT35-2 only reaches `partial_delivery_blocked` after a prior `partially_delivered` while C was still collecting. After `pdb → running`, the official node reopens the format *before* another reconcile, so it never re-enters this hole.

**Why this is P0, not inherited P2.** Task 3.5 success criteria require: when there is delivery, remaining selected objects are terminally blocked, and nothing is running, the project enters `partial_delivery_blocked`. They do not say “only if a sibling was still continuable at first delivery.” A-only + HTML + PPTX is a first-class selection. A delivered / B blocked before the first coordinator tick is a first-class ordering. From that state the project cannot complete, cannot block, cannot mark pdb, cannot explicit-reopen, cannot rebind. That is an unrecoverable terminal-state failure, not a missing label.

**Minimal remediation.** Codex must authorize a 3.4-table amendment (outside the 3.5 file list):

1. Declare `running → partial_delivery_blocked` and `awaiting_user → partial_delivery_blocked` with the existing `g_project_partially_delivered_partial_delivery_blocked` keys.
2. In `PartialDeliveryCoordinator.reconcile`, try that target from `running` / `awaiting_user` after `complete` and `blocked`, before `partially_delivered`.
3. Add a system-temp / pytest case that first-reconciles from `running` with A HTML ready and B blocked (no continuable sibling), and a second case A-only HTML ready + PPTX blocked.
4. After `pdb → running`, if remainder is still exhausted, the new edge must take the project back to pdb on silent reconcile.

There is no correct 3.5-only workaround. A two-step through `partially_delivered` is illegal because that guard requires `selected_objects_continuable`.

### P1 — `conditions()` does not pin to the bound selection

**Evidence.** After binding v1 `A,B + pptx` with A HTML+PPTX `delivery_ready` and B `evidence_blocked`:

- `reconcile(v1)` does not complete (`all_selected_html=False`).
- `conditions(DeliveryContract(same id, same version, reports=("A",), pptx))` returns `all_selected_html=True` and `all_selected_optional_formats_delivery_ready=True`.
- `conditions(unbound v2, A+pptx)` reports the same would-complete flags without writing a v2 bind.
- `reconcile` of the slim same-version contract still raises `ContractDriftError`.

**Inference.** Write path honors immutability. The public read API that the module advertises as the mechanical source of aggregate booleans does not. “删掉失败对象获得完成” succeeds on `conditions()` for the same contract identity. Downstream that displays or decides from `conditions()` can claim complete without a new contract version.

**Minimal remediation.** After `_validate_coordinator_events()`, if `(contract_id, contract_version)` is already bound, require the argument selection to match or raise `ContractDriftError`. If a lower version is passed after a higher bind, raise `ContractDriftError`. Unbound *higher* version can stay a preview, but must not be confused with a bound complete; prefer requiring an explicit bind via `reconcile`/`reopen_*` before treating those booleans as authoritative.

### P2

1. **`rebind_report` returns stale `CoordinationResult.conditions`.** Probe: after legal `report_A → report_A_v2`, `result.conditions` still lists `report_A`; a fresh `conditions()` lists `report_A_v2`. Cause: conditions are computed from the pre-append view. Next write/read rebuilds correctly. Fix: re-validate or apply the new rebind onto the view before returning.
2. **Official nodes do not cover the P0 ordering.** Not a second product bug; it is why the suite is green. Any 3.5 follow-up must add the simultaneous-exhaustion cases or this will regress.

Non-blocking observations (not in the P2 count):

- New contract version that drops a blocked report and then completes is the specified explicit reselection path. It works.
- One project reopen receipt can rebind every kind. Ledger is per-kind. Reasonable for one user-material acceptance; confirm if Codex wants one reopen per kind.
- `remaining_selected_exhausted_blocked` is aliased to `not continuable`. Redundant with `no_running_selected_object`. Harmless today because `complete` is tried first.
- `graph/__init__.py` does not export recovery. Matches the 3.5 “export only if necessary” scope.

### Challenge to the apparent plan

The implementation and the two official nodes are internally consistent with a hidden ordering assumption: “there is always a continuable selected object at the moment the first artifact becomes ready, and after every project reopen someone will reopen a format or start a new report object before the next reconcile.” v1.2 prose, Task 3.5 scope, and a user who selected only A+PPTX do not grant that assumption. Accepting on green GT35-1/GT35-2 would accept a coordinator that deadlocks the most compact real selection matrix.

I also reject the fallback that “3.4 already froze the table, so 3.5 is done.” 3.5’s job is the aggregation outcome. If the frozen table cannot express that outcome, 3.5 is not acceptable until Codex opens the table.

## Evidence And Assumptions

**Evidence**

- Official nodes: 2 passed / 0.20s on `.venv` 3.13.
- v1.2 §10.2: `partially_delivered` = still continuable; `partial_delivery_blocked` = delivered + remainder exhausted; complete = every selected HTML and every selected optional format `delivery_ready`; selection change = new contract version; report/format isolation.
- `recovery.py` binds selection on first write API, fail-closes same-identity drift, monotonically rejects older versions, classifies per object, submits only via `GraphExecutor.submit`, validates coordinator events on every read.
- `TRANSITION_REGISTRY.declared("project", "running", "partial_delivery_blocked") is None`.
- Deadlock probe event order: objects reach delivery/block, then only `coordinator.selection_bound`; project stays `running`; reopen/rebind refused.
- Forged selection/rebind digest, event id, key, receipt, extra keys, duplicates, chain break, stale receipt: all `CoordinatorEventContractError`.
- Legal replays of selection bind, rebind, format reopen, project reopen: no extra events.

**Assumptions**

- Task 3.4 table remains the runtime boundary unless Codex authorizes an edit.
- `conditions()` is a public coordination API, not an internal helper.
- New-version drop of a failed report that then completes is intended, not a cheat.
- No visual / live-web / clinical authority is claimed from these probes.

**Uncertainty**

- Whether Codex treats the missing `running → pdb` edge as a 3.4 inherited gap (then 3.5 could be forced PASS) or as a 3.5 acceptance blocker (this verdict).
- Whether `conditions()` same-version unpin is P1 (this verdict) or P2 if Codex defines it as a pure function of the argument contract.
- Whether one reopen receipt per kind is required.

## Risks, Gaps, And Verification Needs

- **Acceptance risk:** green official nodes hide an unrecoverable project state for A-only+PPTX and for “B already blocked before first reconcile.”
- **Recovery risk:** from the stuck `running` state, the 3.5 reopen/rebind machinery cannot start. That is worse than a wrong label.
- **Read-path risk:** `conditions()` can report complete for a drifted same-version selection.
- **Not verified here:** full-repo pytest, Ruff, mypy, package/diff gates, Task 3.4 graph regression, CLI/fixture, portal/render, PPT Master, browser/PDF/PPT/visual.
- **Follow-up verification after any fix:** the four system-temp cases in P0 remediation, plus `conditions()` same-version drift, plus `rebind_report` return-value targets, plus post-`pdb→running` silent reconcile when remainder is still exhausted.

## Recommended Next Step

Codex should **not accept Task 3.5**. Authorize a narrow cross-task edit:

1. Add `running → partial_delivery_blocked` and `awaiting_user → partial_delivery_blocked` (same guard keys).
2. Update `reconcile` candidate order.
3. Pin `conditions()` to the bound selection for the same `(contract_id, version)`.
4. Recompute `CoordinationResult.conditions` after a successful rebind append.
5. Add the simultaneous-exhaustion tests the official nodes omitted.

Do not attempt a 3.5-only fake two-step.

### Objections, proposed solutions, decision points, bounded questions

**Objections**

1. Official-node green is not v1.2 completeness. The suite never first-reconciles delivery+exhaustion from `running`.
2. “Table is frozen, coordinator is correct” is not an acceptable 3.5 close. The success criterion is the project terminal, not the boolean struct.
3. `conditions()` as an unbound calculator contradicts “同一合同身份下选择漂移失败关闭.”

**Proposed solutions**

- P0: declare the missing pdb edges; try them from `running` / `awaiting_user`.
- P1: fail-close `conditions()` on bound-selection drift / version inversion.
- P2: refresh view after rebind before returning.

**Decision points for Codex**

1. Open the 3.4 transition table for the two pdb edges, or reject 3.5 until that happens.
2. Is `conditions()` required to honor the bound contract (P1) or only the write APIs (downgrade to P2)?
3. Confirm that v2 dropping a blocked report and completing is the approved explicit reselection path.

**Bounded questions**

1. May transitions.py / guards.py be edited in a 3.5 follow-up to add `running|awaiting_user → partial_delivery_blocked`? This decides whether 3.5 can be made acceptable at all.
2. Should `conditions()` raise `ContractDriftError` on same-version selection mismatch after bind? This decides P1 vs P2.
3. After `pdb → running`, if nothing was actually rebound or reopened, should silent `reconcile` immediately return to `partial_delivery_blocked`? I recommend yes.

**Safe provisional path if Codex does not answer:** keep FAIL; do not ship 3.5; do not treat GT35-1/2 as acceptance.

## Verdict

FAIL

P0=1; P1=1; P2=2
