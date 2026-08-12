Verifying source hashes, running the three-file pytest, and executing temporary adversarial probes now.Hashes match and tests passed. Reading remaining critical paths and running temporary adversarial probes.All source hashes matched, the three-file suite passed, and 70/70 temporary adversarial probes passed. Drafting the completion report.

# Conference Participant Output: ci_phase3_task33_acceptance - general_grok45_completion

## Boundary Check

- Role: `general_grok45` / Grok Build / grok-4.5; same session completion round.
- Workspace only: `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`.
- Read-only: no repo writes; did not read other participant output.
- Temporary probes under system temp only; cleaned after run (`/var/folders/.../ci33_probe_*` removed).
- Did **not** self-write `runs/conference/ci_phase3_task33_acceptance/general_grok45_completion.md` (runner persists this response).
- No production paths; no visual/PPT/browser final acceptance claimed.
- Read set limited to the authorized Task 3.3 files (plus runtime imports exercised by tests/probes).

## Independent Work Product

### Source digests (verified)

| File | Expected SHA-256 | Observed |
|---|---|---|
| `src/ci_workflow/ingestion/manual_inbox.py` | `128c9a40…457481` | match |
| `schemas/download-request.schema.json` | `b614cd11…9968c5` | match |
| `tests/integration/test_manual_inbox_recovery.py` | `1ddfe481…0a7b369` | match |
| `tests/integration/test_user_filename_auto_rename.py` | `54dea9ec…139063d8` | match |
| `tests/integration/test_download_request_transitions.py` | `c09cbab7…a1115bc` | match |

Also read: `policies/gates/B-v1.yaml`, `src/ci_workflow/application/project_service.py` (scaffold only: creates `evidence/manual-inbox`, empty `receipts/download_requests.jsonl`, seed `logs/download_requests.md`).

### Exact tests

```text
uv run pytest tests/integration/test_manual_inbox_recovery.py \
  tests/integration/test_user_filename_auto_rename.py \
  tests/integration/test_download_request_transitions.py -q
→ 3 passed in 1.08s
```

Test counts are **not** treated as acceptance proof; probes below are decisive.

### Adversarial temp probes (70/70 PASS)

Independent `ManualInboxService` project tree in a system temp dir. Challenges and outcomes:

| Challenge | Result | Anchor |
|---|---|---|
| Uppercase `.PDF/.HTML/.TXT`, keep original name | ACCEPTED; original in metadata only; library uses lower-ext canonical name | e.g. `Paper.PDF` → `nct…-publication-pdf-v1-….pdf` |
| Crash after `file_detected`, re-scan | resumes to `accepted` | scan path |
| Crash after `matched`, re-scan | +1 accept event, +1 job, +1 SQLite `source_versions` row | event/job/SV counts |
| After `accepted`, leftover inbox copy | cleaned; **no** new events/jobs/SV; path stable | counts unchanged on replay |
| Same-run multi matching files | `needs_re_download`; ≥2 quarantine paths | fail-closed |
| Same-run two active requests, overlapping IDs | quarantine reason: 文件同时匹配多个下载请求… | fail-closed |
| Cross-run same DOI/NCT | distinct `request_id`/inbox; new run accepts; old stays `awaiting_user` | isolation |
| English title ≥2 non-generic words | accept when both hit; quarantine when only generics | `_title_matches` + scan |
| No DOI/PMID/registry | `RequestNotRequiredError` 中文; no ledger row | create guard |
| gap closed / extension unit / non_blocking | all rejected | GateSpec B critical units |
| Multi-round bad files | `处理说明.md` keeps `bad1`+`bad2`; paths ≥2; attempt≥2 | quarantine notes |
| Download list | 中文标题/说明；`放入：`+`无需重命名`；no state/backend labels/✓ | `logs/download_requests.md` |
| accepted model ↔ Schema ↔ SQLite ↔ jobs | Draft202012 validates; SV row exists; job `source_version_id` matches | 7 accepted ledger rows schema-valid |
| DOI/NCT/PMID normalize | trailing DOI punct, lower NCT, PMID digits | content match ACCEPTED |
| Fake PDF / HTML as `publication_pdf` / login / unreadable | all `needs_re_download` with 中文 reasons | fail-closed |
| Identity drift same `request_id` | `DownloadRequestError` | fail-closed |

### Design claims confirmed in source (evidence, not inference)

- Six declared transitions + `not_required` from open states; undeclared rejected (`_DECLARED_TRANSITIONS`).
- Request only if blocking + gap open + critical units + expected_to_close intersects missing + real GateSpec id/fingerprint + at least one verifiable ID (`create_request` ~724–788).
- User path contract in list line: title/reason/URLs/`放入：evidence/manual-inbox/<id>`/`无需重命名` (`_request_list_line`).
- Scan derives media type from extension (case-insensitive); no rename required (`_media_type_for` + `scan_and_process_inbox`).
- Idempotent events via `idempotency_key` including attempt + digest; accept short-circuits; re-extraction job same-id conflict fail-closed.
- Canonical archive under `evidence/library/<request_id>/…`; original filename only on request/job metadata.
- `project_service` only scaffolds dirs/seed files; business logic lives in `ManualInboxService` (expected for this task slice).

### Defects found

**P0:** none  
**P1:** none  

**P2-1 — Direct `accept()` after ACCEPTED does not clean leftover inbox files**  
- **Where:** `manual_inbox.py` `accept()` early return when `state is ACCEPTED` (≈1366–1367); cleanup only in `match_and_accept` ACCEPTED branch (≈1128–1135) and therefore the **scan** path.  
- **Repro (probe):** after accepted, write leftover to inbox; call `accept(...)` → file remains; call `scan_and_process_inbox` → file removed.  
- **Actual / expected:** direct API no-op leaves copy; product user path (scan) cleans.  
- **User impact:** none if only scanner is used; residual clutter if a caller uses `accept()` alone after crash.  
- **Minimal fix:** in `accept()` ACCEPTED branch, if content digest matches, `unlink` inbox original like `match_and_accept`.  
- **Regression name:** `test_accept_accepted_cleans_inbox_leftover`.

**P2-2 — Quarantine note may add an extra “未能识别文件名的附件” line**  
- **Where:** `scan_and_process_inbox` quarantines named files via `_quarantine_file`, then `_quarantine` may append a second note using `original_filename or "未能识别文件名的附件"` when still `awaiting_user` (≈1278–1281).  
- **Repro:** first bad file in empty request → note has both `bad1.html` and generic line.  
- **Impact:** multi-round history still correct; slightly noisy 中文说明.  
- **Minimal fix:** skip generic note when scan already recorded named quarantines for this pass.  
- **Regression name:** `test_quarantine_note_no_duplicate_generic_line`.

### Highest-impact objection (challenged and resolved)

**Objection:** “3 passed” alone can hide false green (unexecuted crash branches, cross-run bleed, English-title single-token match, schema/SQLite drift).  
**Challenge result:** temp probes executed those branches against real FS + EventStore + jsonl jobs + SQLite `source_versions`; no P0/P1 false green found. Residual P2 is API-edge hygiene, not the user “download → keep name → put in one folder” path.

### Concrete remediation priority (if hardening)

1. Align `accept()` ACCEPTED cleanup with `match_and_accept` (P2-1).  
2. Deduplicate quarantine note generic line (P2-2).  
3. Optional later: expand English stopword set if clinical titles prove noisy (not demonstrated fail).

## Evidence And Assumptions

**Evidence (observed)**  
- SHA-256 of five task artifacts match conference packet.  
- `uv run pytest` three files: `3 passed in 1.08s`.  
- 70 temp probes all PASS; temp dir cleaned.  
- Accepted ledger rows validate against `download-request.schema.json`.  
- SQLite `source_versions` columns include `source_version_id`, `content_sha256`, …; row present and linked from jobs.  
- Download list and quarantine notes are Chinese clinical copy without machine state enums.

**Inference**  
- Production user path is intended to be: system creates request + Chinese list with folder path → user downloads keeping publisher filename → system scan processes; not multi-step rename/classification by user.  
- `project_service` scaffolding without calling `ManualInboxService` is acceptable for Task 3.3 module acceptance; full orchestration may be a later task.

**Assumptions**  
- Acceptance boundary is Task 3.3 ingestion/request machine as implemented, not full end-to-end CLI/UI orchestration.  
- Real NCT IDs are `NCT`+8 digits (pattern in code); short forms in older synthetic tests rely on DOI/PMID for match.

**Uncertainty**  
- Did not exercise OCR, live downloads, Task 3.4+, report rendering, or multi-process concurrent scanners.  
- Did not claim clinical/regulatory authority over gap selection upstream of `create_request` (caller supplies `gap_still_open` / units).

## Risks, Gaps, And Verification Needs

- **Residual P2:** direct `accept()` leftover cleanup; noisy quarantine generic note.  
- **Upstream dependency:** correctness of “only when still blocking” depends on callers setting `gap_still_open` / units honestly; module guards are fail-closed given those inputs.  
- **Not verified here:** concurrent scans, partial disk full mid-`os.replace`, full package-manifest/export wiring.  
- Codex remains final authority for any product-level go/no-go beyond this module audit.

## Recommended Next Step

1. **Codex:** treat Task 3.3 module acceptance as **PASS** (P0=0, P1=0) based on hash-locked sources + three integration tests + independent FS/SQLite/event/job probes.  
2. Optionally schedule low-priority hygiene for P2-1/P2-2 before broader E2E wiring.  
3. Do not block Task 3.4+ solely on the P2 API leftover edge if scan is the only production entry.

## Verdict

**PASS; P0=0; P1=0; P2=2**
