# Phase 1 Independent Verification

I read the full `/Users/smkzw/.hermes/SOUL.md` (all sections including §12 Conference And Execution Rules) and complied with it.

## Boundary And Sources Read

Read-only audit inside the workspace. No production paths touched. No edits made. Temp verification project created outside the repo and fully removed.

Read:
- `context/ci_phase1_exit_context.md`
- `.trellis/tasks/08-11-phase-1-project-truth-base/{prd,design,implement}.md`
- `docs/decisions/0004-phase-1-contract-boundaries.md`
- `docs/acceptance/runs/phase-1-exit/regression.txt` and `anchors/runtime.json`
- `migrations/0001,0003,0005,0006,0008_*.sql`
- `tests/integration/test_sqlite_migrations.py` (full)
- Phase 1 source referenced by the deterministic suite: `storage/{paths,event_store,checkpoint_store,snapshot_store,manifest_store,content_store}.py`, `application/{project_service,capability_preflight}.py`, `domain/{evidence,contracts}.py`, `cli.py`
- Per-task exact suites (`green.txt` for task-1.1…1.6) to reconstruct the exit command
- `schemas/source-receipt.schema.json`, `schemas/evidence-gap.schema.json`

## Commands Reproduced

`regression.txt` records "62 passed in 1.12s" but **does not record the literal command**. I reconstructed the approved exit suite as the union of the per-task exact suites (from each task's `green.txt`) — the union of tasks 1.1–1.6 exact suites plus Task 1.6's 11th node `tests/contract/test_capability_matrix.py`:

```
PYTHONDONTWRITEBYTECODE=1 uv run --frozen pytest -p no:cacheprovider -q \
  tests/unit/test_ids.py tests/unit/test_state_enums.py tests/unit/test_content_store.py \
  tests/contract/test_project_contract.py tests/contract/test_evidence_audit_contracts.py \
  tests/contract/test_artifact_manifest.py tests/contract/test_capability_matrix.py \
  tests/integration/test_project_workspace.py tests/integration/test_project_move_portability.py \
  tests/integration/test_artifact_paths.py tests/integration/test_sqlite_migrations.py \
  tests/integration/test_append_only_records.py tests/integration/test_source_version_chain.py \
  tests/integration/test_event_checkpoint_replay.py tests/integration/test_snapshot_identity.py \
  tests/integration/test_capability_preflight.py
```
Result: **62 passed in 0.59s** (matches recorded 62).

Full regression and quality gates (all executed, all green):
- Full repo pytest: **133 passed in 5.68s** (matches)
- Focused SQLite lineage (`test_sqlite_migrations.py` + `test_append_only_records.py`): **7 passed in 0.10s** (matches)
- `ruff check src tests`: All checks passed
- `mypy --strict src`: Success, 20 source files
- `ci-workflow package verify --root .`: PACKAGE_OK
- Trellis validate: passed; `git diff --check`: clean

Caveat (P3/non-blocking): the exit `regression.txt` omits the literal deterministic command, relying on "62 passed" alone. It was reproducible, but the exact command should be recorded for future auditability.

## Runtime Anchor Audit

Real anchor `runtime.json` (executed_at 2026-08-11T21:55:31+08:00, `source_commit` c9dea6d = current HEAD) — every claim independently reproduced:

1. **Project create/move/verify through public CLI.** I created A/B/C × html,pdf,html-ppt,pptx, then moved+renamed the project dir, and `ci-workflow project verify` returned `PROJECT_OK…合同版本 1`. Scan of 11 non-SQLite persisted files found **zero** absolute machine paths (anchor claims 12 files — its evidence-chain project had one extra persisted file; count difference is expected, not a defect).
2. **SQLite integrity.** `PRAGMA integrity_check` = `ok`, `user_version` = `8`, `foreign_keys` enforced via app connection. Contract row persisted with `Asia/Shanghai` and `data_cutoff=2026-08-10T23:59:59.999999+08:00`.
3. **Orphan project lineage.** All three trigger guards in `0008_project_lineage_guards.sql` reject orphan inserts:
   - `gate_evaluations`: `project lineage: gate_evaluations` (SQLITE_CONSTRAINT_TRIGGER=19), 0 rows
   - `report_snapshots`: `project lineage: report_snapshots` (19), 0 rows
   - `correction_proposals`: `project lineage: correction_proposals` (19), 0 rows
   `coverage_sets`/`coverage_projections` transitively guarded via FK to `report_snapshots`. `project_runs` has FK to contract versions. All project-scoped tables are lineage-bound.
4. **Absolute-path portability.** `ArtifactPathService.validate_persisted_path` (paths.py) rejects absolute/jump/backslash paths and enforces the 4-part `reports/A|B|C/vN/artifact` contract. `verify_project_workspace` runs `_assert_no_absolute_values` over every persisted JSON (project.yaml + initial JSON files) and cross-checks DB contract vs project.yaml. `ManifestStore._artifact_path` rejects paths escaping project root.
5. **Event replay after cache loss.** `EventStore` (events.jsonl) is the canonical source; `CheckpointStore.replay` validates `event_stream_digest` and `applied_event_ids` against the live stream, so a deleted private cache cannot affect recovery. Test `test_event_checkpoint_replay_is_idempotent_without_framework_cache` removes `.langgraph-cache`, re-replays, asserts no duplicate side effect, tamper rejection, and crash-window recovery — passes.
6. **Source date separation.** `SourceVersionRecord` carries four distinct date roles (acquired/published/effective/first_disclosed) with `DateEvidence` enforcing reported⇒value, not-disclosed⇒null. Test asserts all four roles in `source_date_assertions`, offsets present, dedup by content digest, effective_at null when not_publicly_disclosed — passes.
7. **Complete receipt/gap fields.** `source-receipt.schema.json` requires full audit set incl. `completeness_checks`/`alternative_paths` (minItems=1), `content_sha256` (required on acquire), `error_class` (required on non-acquire), `parent_attempt_id`, `recovery_round`; `evidence-gap.schema.json` requires `candidate_sources`/`information_gain_diff` (minItems=1), `next_legal_action`. `test_evidence_audit_contracts.py` covers missing-field failure — passes.
8. **Immutable snapshot identity.** `SnapshotStore` content-addresses manifests; test asserts same content ⇒ same id, changed content ⇒ different id+path, move-readback works, tamper ⇒ `SnapshotIntegrityError` — passes.
9. **Accepted manifest current-run binding.** `ArtifactManifest` requires every Appendix C field; `ManifestStore._verify_current_context` rejects accepted manifests whose full identity ≠ current `ManifestWriteContext` (and requires a context at all). `_verify_artifact` cross-checks digest/bytes/mtime. Test asserts write fails without/with-wrong context, and tampered artifact rejected — passes.
10. **Selection-aware capability preflight.** Reproduced on the real project with `public-http,public-browser`: **10 applicable ready, login_browser+ocr not_applicable, 12/12 deliveries ready, overall_state=ready** — exactly matching the anchor. Source confirms `_applicable_capabilities` only adds capabilities for selected routes/outputs; `_delivery_dependencies` maps per-output requirements; missing PPTX blocks only PPTX (test `test_missing_pptx_capability_blocks_only_pptx_and_gives_plain_chinese_guidance` asserts `HTML、PDF 不受影响` and no `gate`/`signal` English tokens) — passes.

Anchor's `sha256` values (manifest `01a7b0ca…`, capability `094ada24…`) are self-consistent digests recorded at anchor time; I did not reproduce identical digests because the anchor's base selection (`needs_document_ingestion=True` from project) and canonical payload differ from my CLI invocation — not a defect, but the digests are not independently recomputable here (P3 note).

## Findings

- **P0: 0**
- **P1: 0**
- **P2: 2** (non-blocking, no repair required for acceptance)
  - P2-1: `docs/acceptance/runs/phase-1-exit/regression.txt` does not record the literal deterministic command (only "62 passed in 1.12s"). It is reproducible from per-task suites, but the exact exit command should be persisted for auditability.
  - P2-2: Anchor `conflict_sets`/`content_blobs`/`source_date_assertions` digests are recorded but not independently recomputable from the anchor alone (base selection/payload not embedded); the underlying claims are covered by executed tests.
- **P3: 2** (informational):
  - P3-1: Anchor's `checked_non_sqlite_files_without_absolute_paths: 12` vs my bare project's 11 — the anchor's evidence-chain project had one additional persisted chain file; count is scenario-dependent, not a defect.
  - P3-2: `PRAGMA foreign_keys` shows 0 on a raw `sqlite3` CLI connection unless explicitly enabled; the application's `open_database` enables it and the migrations test asserts `foreign_keys=1`. Not a product defect.

## Verdict

**PASS** — P0=0 and P1=0. The deterministic 62-node exit suite is reproduced green, the full 133-test regression and all quality gates pass, and every Phase 1 risk area (orphan lineage, absolute-path portability, event replay after cache removal, source date separation, receipt/gap completeness, immutable snapshot identity, accepted-manifest current-run binding, selection-aware capability preflight) has a real executed anchor. The two P2 findings are documentation/digest-reproducibility notes, not acceptance blockers.

## Codex-Owned Final Checks

- Confirm the delegated agent stayed inside allowed paths (temp project created under `/tmp`, removed; no repo edits).
- Confirm only the runner-managed output path `runs/pi_ci_phase1_exit.md` was produced (I did not write it).
- Browser/visual acceptance of the rendered phase anchor (`browser_anchor: 真实 Chromium 页面已完成渲染`) is asserted in the anchor but I did not re-render Chromium — Codex final authority for visual acceptance.
- Final clinical/regulatory/current-web claims are Codex-owned; I made none.
- Recommend Codex record the literal deterministic exit command in `regression.txt` (P2-1) before finalizing.
