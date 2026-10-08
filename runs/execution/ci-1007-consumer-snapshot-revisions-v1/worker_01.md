# Execution Output: ci-1007-consumer-snapshot-revisions-v1

## Scope and Actual Route

- **Fallback declaration:** primary route `codebuddy/codebuddy-cli/deepseek-v4.1-flash:max` was unavailable before a resumable session existed; this work ran on the declared fallback `zcode` / `GLM-5.3-Flash` (ZCode harness). No effort attestation is claimed from requested flags; runner owns actual runtime receipts.
- **Capability/provenance limitation (explicit):** the complete root-cause batch (migration 0018, five application-module changes, new test family, four test adaptations) was found **already on disk** from the interrupted primary attempt, matching exactly this task's allowed-file envelope. This fallback **authored none of those bytes**; it fully audited every changed line against the task contract, found no gap requiring further edits, and performed the verification below. Zero additional product/test edits were made by this session.
- **Edit-surface application note:** the contract requested `apply_patch`; no edits were ultimately required. Had any been needed, the harness-equivalent surgical Edit tool would have been used.
- Repository-only work at explicit cwd; legacy Chinese workspace untouched; no git state mutations; owner dirty files and unrelated untracked artifacts preserved; no actual `.artifacts` project writes (tests used pytest tmp projects only); no commit/push; no recursive dispatch, conference, browser, or external research.

## Changes

All found on disk from the primary attempt and audited line-by-line by this fallback:

Production (exact files):
- `migrations/0018_snapshot_scoped_portal_consumers.sql` (new, untracked): rebuilds `source_portal_consumer_bindings` with uniqueness rescoped from `(fact, report)` to `(fact, report, evidence_snapshot_id)`; `INSERT ... SELECT *` preserves every legacy row's binding_id/payload/sha256/timestamps byte-for-byte; keeps append-only no-update/no-delete triggers; adds snapshot index; drops the obsolete `(fact, report)` unique index. 0001–0017 untouched.
- `src/ci_workflow/application/c_portal_consumer_registry.py`: same-snapshot conflict preflight (`AND evidence_snapshot_id=?`); snapshot-qualified `stable_id` binding ids; C projection (`project_reviewed_c_source_states`) reads bindings of the exact snapshot only, passes `evidence_snapshot_id` into binding validation, and rejects two conflicting consumer declarations for one row within the same snapshot (no first/last-wins).
- `src/ci_workflow/application/portal_consumer_registry.py`: A efficacy/safety, B baseline, and B shared registration preflights scoped to the exact snapshot; snapshot-qualified binding ids; B-shared A-anchor lookup scoped to the exact snapshot (fetchone safe: table constraint makes (fact, report, snapshot) unique).
- `src/ci_workflow/application/portal_consumer_binding_recovery.py`: `_validated_binding` accepts exactly two id forms — legacy pre-snapshot id and snapshot-qualified id — under the scope being exported/restored; anything else fails closed; recovery preflights by exact binding id (full row incl. snapshot) and inside the sidecar's exact snapshot scope; export scoped to one snapshot; A-anchor proof scoped to the exact snapshot.
- `src/ci_workflow/application/user_fact_edit.py`: `_registered_source_bindings` walks the user-revision lineage and fetches all declarations across snapshots; `_scoped_source_bindings` collapses identical declarations, resolves genuine conflicts only by the current rendered source scope, preserves a unique single candidate when no current exists, and fails closed on unresolved ambiguity; `_current_source_scopes` reads `source_evidence_snapshot_id` from the hash-pinned builder input of each committed current report; `initialize_current_delivery` resolves scope from actual caller report-data bytes.
- `src/ci_workflow/application/b_efficacy_source_views.py`: `_verified_a_consumer_proof` selects `fetchall()` scoped to the exact snapshot and requires exactly one verified A identity (no arbitrary history pick).
- `ActiveFactBinding` source (`renderers/portal/active_fact_projection.py`): unchanged, as preferred. Row-hash/semantic guards untouched; no display/page ids moved into scientific hashes; no fact versions duplicated.

Tests (exact files):
- `tests/integration/test_1007_snapshot_scoped_consumers.py` (new): 7 genuine negative/positive contract tests — migration byte-preservation + uniqueness rescope + append-only guards; same fact across two snapshots registers alongside with snapshot-qualified ids + replay idempotency; no-current conflict fails closed while unique candidate is preserved; current delivery selects the legitimate rendered scope; same-snapshot conflict rejected without partial write; recovery binds new ids to exact scope and rejects forged wrong-scope ids; recovery accepts legacy ids only in their original scope and rejects cross-scope reuse and dual id schemes in one scope.
- `tests/integration/test_1007_c_source_review_entry.py`: owner's appended regression preserved untouched (it is the documented RED).
- `tests/integration/test_sqlite_migrations.py`, `tests/integration/test_1007_baseline_edit_consumers.py`, `tests/integration/test_r24_c_consumer_recovery.py`, `tests/integration/test_w04_consumer_binding_recovery.py`: assertions strengthened to the new contract (expected migration list includes 0018; binding-id derivation includes snapshot). No assertions weakened; no historical SHA fixtures changed.

Not touched (owner's, preserved): `tools/materialize_ctgov_c_candidate.py`, `tests/integration/test_r24_c_candidate_materialization.py`, `tests/fixtures/task45-evidence-drawer/source_evidence.py`, `docs/acceptance/runs/8.4/*`, untracked `.playwright-cli/` artifacts.

## Verification

Commands (project `.venv`, cwd repo root) and results:

1. `.venv/bin/python -m pytest tests/integration/test_1007_c_source_review_entry.py -x -q` → **8 passed** (incl. owner's appended regression, previously RED per context).
2. `.venv/bin/python -m pytest tests/integration/test_r24_c_source_consumers.py tests/integration/test_r24_reviewed_c_read_projection.py tests/integration/test_r24_c_consumer_recovery.py tests/integration/test_r24_c_candidate_materialization.py tests/integration/test_w04_consumer_binding_recovery.py tests/integration/test_1007_baseline_edit_consumers.py tests/integration/test_sqlite_migrations.py -q` → **71 passed** in 83.87s.
3. `.venv/bin/python -m pytest tests/integration/test_1007_snapshot_scoped_consumers.py -q` → **7 passed** in 3.30s.
4. `.venv/bin/python -m pytest tests/integration/test_1007_real_fact_editor.py tests/integration/test_1007_c_sample_current_save.py tests/integration/test_1007_historical_save_retry.py tests/integration/test_1007_current_report_edit_navigation.py tests/integration/test_1007_presentation_current.py tests/integration/test_1007_c_locked_source_display.py tests/integration/test_1007_joint_c_bootstrap.py tests/integration/test_1007_c_existing_project.py tests/integration/test_1007_identity_consumers.py -q` → **102 passed** in 127.04s.
5. `MYPYPATH=src .venv/bin/mypy --strict src/ci_workflow/application/{c_portal_consumer_registry,portal_consumer_registry,portal_consumer_binding_recovery,user_fact_edit,b_efficacy_source_views}.py` → **Success: no issues found in 5 source files**.
6. `.venv/bin/ruff check` on the five modules + two test files + `migrations/` → **All checks passed**.
7. `.venv/bin/ruff format --check` on impacted files → 6 files would be reformatted; **not a project gate** (untouched files also flagged; pyproject configures `[tool.ruff.lint]` only). No reformat applied to avoid noise diffs.

Total in-scope regression: **188 tests passed, 0 failed**.

## Evidence

- RED (owner-provided, documented in `context/ci-1007-consumer-snapshot-revisions-v1_execution_context.md`): `test_corrected_display_prepares_new_epoch_without_reaccepting_source_facts` failed with `CPortalConsumerRegistrationError: 已登记 C 消费者身份与当前候选冲突`; the real repaired six-row PN display candidate failed identically at registration. Not re-produced by this fallback (would require mutating the protected dirty tree; the plan explicitly accepts owner RED as decisive).
- GREEN: all commands above; the new family binds to the fix (byte-preservation, snapshot-qualified id derivation, scope-conflict failures, forged-id rejection, current-scope resolution), so it cannot pass against the pre-0018 behavior.
- Completeness audit: `rg "source_portal_consumer_bindings"` over `src/ tools/` — the only readers are the five audited modules (all snapshot-scoped or fail-closed) plus `tools/audit_current_a_refresh_bridge.py` (audit enumeration only, no identity selection) and `tools/materialize_pdf_scope_candidate.py` (`COUNT(*)` only).

## Limits and Next Safe Action

- **NOT_RUN (owner/Codex responsibility, explicitly not claimed):** final scientific acceptance, clinical review, browser/visual acceptance at the four viewport classes, install/packaging gates, release gates, and replay against the real `.artifacts` project. This worker made no actual-project writes and claims no acceptance.
- **Residual risk (bounded):** a legacy binding id carries no snapshot by construction; recovery treats the snapshot-hash-pinned sidecar as the scope authority. Misuse patterns in scope (cross-scope id reuse, foreign scoped ids, dual id schemes in one scope, forged wrong-scope ids) all fail with test coverage; a fully hand-forged sidecar paired with a legitimately restored foreign snapshot could mint legacy-id rows in a foreign scope — bounded by snapshot immutability and sidecar trust boundary. No speculative machinery added.
- Provenance: on-disk batch authored by the interrupted primary attempt, not by this fallback; runner should attribute accordingly.
- Next safe action: Codex owner integrates, replays the real six-row PN candidate end-to-end, and runs its own gates; no further worker action required.
