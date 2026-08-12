All findings are confirmed with event-order evidence. I did not read any worker report, Codex review, or other participant output; probes ran exclusively in system temp dirs and production files are untouched (`git status` unchanged except pre-existing untracked Task 3.5 files). Final report:

# Conference Participant Output: ci_phase3_task35_acceptance - general_pi_qwen38

## Boundary Check

- Worked only inside `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`; all probe state roots created under `tempfile.mkdtemp()` (`/var/folders/.../pi_ci35_probe_*`, `/tmp/pi_ci35_probe.py` script). No production path written; `git status` after probes identical to before (recovery.py/tests untracked pre-session, not modified by me).
- Did not read worker reports, Codex reviews, or other participant outputs. Files read: the assigned initial read set plus `executor.py`, `reducer.py`, `registry.py`, `state.py`, `guards.py`, `transitions.py` bodies, `storage/event_store.py`, `domain/ids.py`, `graph/types.py`, and spec §10.1–10.2/§19.2 — all within the "not a blanket prohibition" evidence allowance.
- Ran the two exact approved nodes: `uv run pytest tests/graph/test_partial_delivery.py tests/graph/test_partial_delivery_blocked.py` → **2 passed in 0.29s** (re-confirmed at end of session).
- No visual/PPT/browser/clinical acceptance performed; no file edits to source; Codex remains final authority.

## Independent Work Product

Method: static audit of `recovery.py` (1612 lines) against frozen Task 3.4 boundaries (`executor.submit` replay precheck, reducer contract re-validation, EventStore idempotency), then 40+ system-temp probes through the real `GraphExecutor`/`EventStore`, including raw forged-event appends and canonical-state/event-order inspection.

### Verified PASSING contracts (probe IDs in parens)

- First reconcile with no candidate transition still persists exactly one `coordinator.selection_bound`; reducer no-op confirmed (P-A1); same-version selection drift fail-closed (P-A2). Duplicate reports/formats, unsorted, unknown format, `banana`/0/-3/True/None versions all fail-closed at construction (P-B). Unbound v1 after v2 fail-closed (P-C1); appended-forge version order fail-closed on read path (I4).
- Complete only when every selected HTML and every selected optional format is `delivery_ready` (P-D1/D2/D4); replay after complete is `already_complete` no-op (P-D3).
- Report/format independence: delivered formats never revoked, blocked report doesn't pollute other reports (P-E). blocked / partially_delivered / partial_delivery_blocked mechanically distinguished; silent reconcile never leaves either blocked terminal (F1–F5).
- Two project + two format block/reopen cycles: each epoch exactly one accepted reopen; replay no-op; reason drift `EventConflictError`; user material cannot reopen formats; delivered HTML stays `delivery_ready` through all cycles (G0–G15).
- Rebind: wrong kind / non-blocked old / object reuse / reason mismatch / no reopen / stale reopen / chain break / reopen reuse all fail-closed; legal rebind anchors exact reopen event id+digest, replay idempotent, old object stays `evidence_blocked` (H1–H13).
- Forged selection digest/event-id/key fail-closed on read path (I1–I3); whitespace old_object_id forge caught by chain continuity (I6); wrong reopen digest and out-of-range occurrence fail-closed (I7/I8); legal replay counter-cases append nothing (K1).

### P0-1 — Stale contract version can be operated after a higher version is bound → premature `complete`

Evidence (probe P-C2/P-C4, canonical event order):
```
2 coordinator.selection_bound v1
3 coordinator.selection_bound v2   (adds pdf)
...A:html delivered; A:pdf NEVER delivered...
11 .accepted project/proj_1 running->complete   ← submitted by reconcile(v1)
```
`reconcile(v1)` after v2 is bound raises nothing (note=`no_candidate` or submits `complete`); `conditions(v1)` computes the matrix on the abandoned selection (still includes dropped/added formats). Root cause: `_ensure_selection_bound` early-returns when the exact `(contract_id, version)` binding exists (recovery.py:1208–1220) and never applies the "旧版本不能在更高版本之后出现" monotonicity check (only reachable for *unbound* versions, lines 1221–1230). The read path enforces it for appended events (I4), the write path does not — asymmetric.

Why P0: violates the acceptance objective 选择合同不可漂移 and v1.2 §10.2 ("每个选定报告的 HTML 及每个选定可选格式均 delivery_ready" for complete; "不得把放弃的产物静默算作完成") under plain legal API usage (no forgery needed): the project reaches terminal `complete` while the current bound selection (v2) still requires an undelivered pdf. Also contradicts the module's own docstring invariant (lines 10–11). Affects all public actions (`reconcile`, `conditions`, `reopen_project`, `reopen_format`, `rebind_report`).

Minimal remediation: in `_ensure_selection_bound`, before/inside the recorded-binding early return, compute `max(b["contract_version"] for b in view.selection_bindings if b["contract_id"] == contract.contract_id)` and raise `ContractDriftError` when `contract.contract_version < max`. Apply the same check in `conditions()` (which bypasses `_ensure_selection_bound`). Add regression: bind v1→v2, then stale-v1 reconcile/conditions/reopen must raise.

### P0-2 — Whitespace-variant forged `coordinator.report_target_bound` passes the unified validator, hijacks target resolution, and permanently wedges the legitimate rebind

Evidence (probe I5): appended a forged rebind with `new_object_id="report_B_v2 "` (trailing space) carrying the correct recomputed event_id/idempotency_key/digest/reopen receipt. `conditions()` did **not** raise; B's resolved target became `'report_B_v2 '` (hijack confirmed). The subsequent legitimate `rebind_report(..., new_object_id="report_B_v2")` then fails `CoordinationError` because the forged event already consumed the reopen receipt (I5b) — recovery for that kind/epoch is permanently wedged by one forged line.

Why P0: the acceptance objective explicitly requires 报告版本重绑和共享事件库读路径不可伪造, and the module docstring (lines 17–21) promises every forged/mismatched/drifted coordinator event fails closed "在影响状态、选择或目标解析之前". This forge influences target resolution. Root cause: write path normalizes ids via `" ".join(x.split())` (lines 693–694) and `stable_id` normalizes internally, but `_validate_rebind_event` compares raw payload strings and accepts non-canonical ids; every other forge vector (digest, event id, key, chain, stale receipt, whitespace *old* id) is caught.

Minimal remediation: in `_validate_rebind_event`, reject non-canonical ids outright — `if old_object_id != " ".join(old_object_id.split()) or new_object_id != " ".join(new_object_id.split()): raise CoordinatorEventContractError` (fail-closed is stricter and simpler than normalizing). Add regression: trailing/internal-whitespace forged rebind must raise on read path.

### P1-1 — Second `awaiting_user` reopen stalls permanently; awaiting reopen identity collides with blocked reopen identity

Evidence (probes J2, J5):
```
J2: create → selection → running->awaiting_user → reopen#1 accepted (running)
    → running->awaiting_user (cycle 2)
    reopen#2 → note=replay_noop, SAME event as reopen#1, grew=0,
    canonical project = awaiting_user   ← permanently stuck
J5: blocked reopen accepted (entry:1) → awaiting_user → awaiting reopen
    → replay_noop returning the BLOCKED reopen's event; project stuck awaiting_user
```
Escape routes also dead: different reason → `EventConflictError` (J3); `new_contract_version_reopens` → rejected with `vNone` comparison (J4). Root cause: reopen request identity is `("project", "running", f"entry:{blocked_epoch}")` (lines 502–504) — it omits `from_state` and any awaiting-entry generation, so (a) every awaiting_user cycle shares epoch 0, and (b) an awaiting reopen collides with a blocked reopen at the same blocked epoch. Note the J4 `vNone` rejection is *correct* per spec (new-contract-version reopen only applies to blocked/pdb sources), but it removes the last escape hatch from the J2 stall.

Why P1 (not P0): the enumerated contract 重复阻断可恢复 (block/reopen generations) is intact — blocked epochs increment correctly (G11 distinct events); the stall is on the `awaiting_user → running` path, which `reopen_project`'s docstring scopes to "blocked / partial_delivery_blocked -> running" even though the code accepts it once. It is a real functional stall on a public API exercising a v1.2 §10.2 declared edge, hence P1; see bounded question 1 for scope decision.

Minimal remediation: include the source state and its entry generation in reopen identity, e.g. count accepted transitions *into* `current` for the object (replay-stable, distinguishes cycles): `identity_parts = ("project", "running", f"from:{current}", f"cycle:{entries_into_current}")`. Mirror in `reopen_format` (format identity already includes object id + blocked epoch; format has no awaiting state, so only project needs the fix). Add regression: two consecutive awaiting_user interruption cycles both reopen.

### P1-2 — Format `new_contract_version_reopens` is structurally dead despite being a v1.2-listed legal reopen reason

Evidence (probe L1): format blocked under v1; `reopen_format(contract_v2, reason="new_contract_version_reopens")` → `CoordinationError: 新合同版本重开需要高于进入阻断时的版本 vNone，当前 v2 不是更新的版本`. Root cause: `_blocked_entry_info` reads the block-time version from `guard_evidence.contract_version` (lines 868–876), but format block transitions (`format_recovery_exhausted`, frozen Task 3.4 table) never carry contract evidence, so `version_at_blocked` is always `None` and the check at lines 615–625 always rejects. v1.2 §10.2 format `blocked -> queued` explicitly lists 新合同版本明确重新打开, and `FORMAT_REOPEN_REASONS` advertises it. Environment/generator reasons still work, so formats remain recoverable — hence P1, not P0.

Minimal remediation (within recovery.py): when `version_at_blocked is None`, derive the version in force at block time from the latest `selection_bound` with sequence ≤ the block entry sequence (data already visible in `_validate_coordinator_events`'s ordered loop; record binding positions). Escalate to Codex if this is considered a frozen-table gap instead (bounded question 2).

### P2 findings (non-blocking, ownership assigned)

- **P2-1 (observation, Task 3.4 boundary):** a perfectly-shaped forged `graph.transition.accepted` reopen appended directly to the store passes reducer guard re-evaluation (my probe supplied valid evidence) and can anchor a coordinator rebind (probe M). This is consistent with Task 3.4's accepted trust model (append-only local store, contract-shape validation, no signatures) — Task 3.5's own validator covers only coordinator-owned events, and it held everywhere. Ownership: record as accepted boundary in Task 3.5 acceptance notes; any hardening belongs to a future security-scoped task (out of approved scope per AGENTS.md).
- **P2-2 (cleanup):** `_selection_material` (recovery.py:1574–1580) is dead code — never called. Ownership: Task 3.5 follow-up cleanup commit.

## Evidence And Assumptions

- Evidence: exact-node run `2 passed in 0.29s` (twice); probe transcript (roots `/var/folders/yb/.../pi_ci35_probe_rr8fext4` and `pi_ci35_ev_*`); line-precise code references above; canonical event-order dumps for P-C4 and J2 reproduced verbatim in the Independent Work Product.
- Inference (marked): J2 severity classification as P1 rests on the reading that 重复阻断可恢复 scopes to blocked terminals [INFERENCE]; if Codex rules awaiting_user reopen in scope, promote to P0. M-series treated as Task 3.4 boundary [INFERENCE from reducer docstring "注册表版本" note and accepted Task 3.4 context].
- Assumptions: frozen Task 3.4 tables/guards are immutable for this task (per context Source Of Truth); EventStore direct-append is the adversary model for "共享事件库读路径不可伪造" (same model the shipped tests use).
- Uncertainty: whether any upstream caller (Task 3.6 CLI) would ever pass a stale contract version — irrelevant to the defect's validity since the API is public and the invariant is documented, but it bounds real-world likelihood.

## Risks, Gaps, And Verification Needs

- P0-1 and P0-2 are both fail-open holes in mechanisms the module docstring claims fail-closed; both are reproducible in ≤15 lines and both have one-location fixes plus regression tests. Until fixed, Task 3.5's two headline guarantees (selection immutability across versions; unforgeable rebind read path) are empirically false.
- P1-1 means any project needing a *second* user-interruption cycle via the coordinator is unrecoverable without manual event surgery — risky once Task 3.6 CLI wires `reopen_project` to user material acceptance.
- Gap in my pass: I did not exercise `executor.replay()`/checkpoint interaction with coordinator events (Task 3.4 accepted boundary; reducer no-op verified by shipped tests), nor multi-run-id isolation beyond the store's own run filtering.
- Verification need after fixes: re-run my probe script (`/tmp/pi_ci35_probe.py`, reusable) — P-C2/P-C4/I5/J2/J5/L1 must flip to fail-closed, all existing OK lines must stay OK; plus the two exact nodes and full suite.

## Recommended Next Step

1. Codex rules bounded questions 1–2 below (scope calls for P1-1/P1-2).
2. One fix round in `recovery.py` only: (a) stale-version monotonicity in `_ensure_selection_bound` + `conditions`; (b) reject non-canonical whitespace ids in `_validate_rebind_event`; (c) reopen identity includes `from_state` + entry generation; (d) block-time version fallback from selection bindings for format reopen (if in scope); (e) delete `_selection_material`. Each with a regression probe mirroring my P-C4/I5/J2/L1 reproductions.
3. Re-convene acceptance: exact two nodes + rerun of this probe suite; P0/P1 must be 0.

Bounded questions for Codex:
1. Is `reopen_project` from `awaiting_user` (v1.2 `awaiting_user -> running`) inside Task 3.5's acceptance contract, or owned by Task 3.3/3.6? Decides P1-1 vs P0. Safe provisional path: fix the identity either way — the current silent `replay_noop` stall is wrong under any scoping.
2. Is the dead format `new_contract_version_reopens` (block-time version unrecoverable from frozen format-block evidence) a Task 3.5 defect to fix via selection-binding fallback, or a frozen-boundary gap to defer? Safe provisional path: implement the binding-position fallback in `recovery.py` (no frozen-table change).
3. Objection to the plan's implicit assumption that "two exact nodes green ⇒ contract holds": the shipped tests never bind v1-then-v2-then-operate-under-v1, never forge whitespace ids, and never drive a second awaiting_user cycle — all three defects live exactly in those untested gaps. Recommend adding them to the permanent suite, not just probe scripts.

## Verdict

FAIL
P0=2; P1=2; P2=2
