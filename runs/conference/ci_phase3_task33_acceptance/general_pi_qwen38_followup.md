All probes complete, repo untouched, temp files cleaned. Final report below.

---

# Conference Participant Output: ci_phase3_task33_acceptance - general_pi_qwen38

## Boundary Check

- Read-only throughout: only the Codex-named read set (`manual_inbox.py`, `project_service.py`, `download-request.schema.json`, the three integration tests, `B-v1.yaml`) plus supporting truth sources needed to verify claims (`domain/ids.py`, `storage/event_store.py`, `storage/content_store.py`, `domain/contracts.py`, `package-manifest.json`, `git diff HEAD`).
- Probes written only to `/tmp/ci_t33_followup/` (5 scripts, 66 executed assertions), run against `tempfile.mkdtemp` project roots, then deleted. `git status --short` after cleanup is byte-identical to before my pass (3 tracked modified files + same untracked set) — no repo write.
- Did not read `general_grok45.md` / `general_grok45_followup.md` or any other participant output. No production paths. Report returned as text for runner persistence.

## Independent Work Product

**1. Exact three-file command (re-executed, not trusted):**
`uv run pytest tests/integration/test_manual_inbox_recovery.py tests/integration/test_user_filename_auto_rename.py tests/integration/test_download_request_transitions.py -q` → **`3 passed in 0.94s`**. Full suite: **`432 passed in 12.69s`**. `ruff check` on all six changed/related files: clean. `mypy --strict` on `manual_inbox.py`: clean. `git diff --check`: clean. Codex anchors reproduce.

**2. Fix-by-fix live verification (my own temp-dir probes, real SQLite/JSONL/events on disk):**

| Original finding | Fix location | Probe result |
|---|---|---|
| P1-1 uppercase extensions | `_media_type_for` lowercases suffix (`manual_inbox.py:481`); error copy rewritten (`:491-505`) | `SUPPLEMENT.HTML`, `PAPER.PDF` (real reportlab PDF, `publication_pdf`), `DATA.TXT` all **accepted**; original filename preserved in metadata; canonical ext lowercased; broken `.PDF` quarantined with reason containing **no** "媒体类型"/media terms (10/10 checks) |
| P1-2 matched→accepted crash wedge | `match_and_accept` MATCHED continuation with digest guard (`:1136-1142`); ACCEPTED leftover-copy cleanup with mismatch guard (`:1128-1135`) | detect→match→"crash"→`scan_and_process_inbox` completes to **accepted**: exactly +1 event, jobs = gaps, `source_versions` +1, inbox emptied; second replay (file reappears pre-unlink) cleans with **0 new events/jobs/source versions**; divergent-content replay fails closed without corrupting the accepted record (14/14 + 2/2 from `file_detected` variant) |
| P2 cross-run deadlock | `_active_others` scoped to same `project_id`+`run_id` (`:669-677`) | new-run inbox with same-paper content **accepted** while old-run request stays active; **same-run** cross-request ambiguity still quarantines (guard not weakened); cross-project same identity doesn't collide (4/4) |
| P2 identity-less request | new guard (`:785-788`) | empty DOI+PMID+registry → `RequestNotRequiredError` with Chinese business reason; zero ledger rows, no inbox dir, list unchanged (5/5) |
| P2 note overwrite | `_record_quarantine_note` append + replay dedupe (`:598-607`) | two bad-download rounds: `处理说明.md` keeps `round1.html` **and** `round2_wrong.html`, no duplicate lines on replay, both quarantine paths persisted and exist on disk (6/6) |
| P2 empty-copy drift | `project_service.py:50` | init seed is **byte-identical** to `_regenerate_download_list` empty output; verified on a real `create_project_workspace` project through create→cancel cycle (3/3) |
| P2 schema/model divergence | `_accepted_requires_archive_metadata` now requires `original_filename` (`:269-270`) | accepted record round-trips against `download-request.schema.json` (Draft 2020-12); hand-built ACCEPTED with `original_filename=None` rejected by Pydantic; all persisted JSONL rows schema-valid (5/5) |
| (new) English title check | `_title_matches` with generic-word stop list (`:450-473`) | registry-only foreign doc with English title matched via 2 distinctive words → accepted; generic-words-only content ("clinical trial results of another study") → quarantined; single distinctive coined word accepted (3/3) |

**3. Ledger/SQLite integrity audit:** events dedupe by idempotency key (`event_store.py:146-162`), re-extraction jobs by stable `job_id` with conflict-aware no-op (`manual_inbox.py:1466-1490`), source versions by `stable_id(source-version, source_id, sha256)` with existence check (`content_store.py:119-126`) — all three confirmed non-duplicating under replay in probes B5–B13. Archive digest verified equal to source bytes (A3). Download list audited for backend terms: no state names, no `gate-spec`, no `request_id` field labels (L triage below).

## Evidence And Assumptions

- **Evidence (executed):** 66 probe assertions across 5 scripts, all green except three initially flagged — two were my probe bugs (manifest walker missed `components.schemas` — schema IS registered at `package-manifest.json:40`; list-term scan false-positived on the inbox directory path, which the contract *requires* the list to contain), one is a genuine residual (P2-1 below).
- **Assumption:** `scan_and_process_inbox` remains the sole operator recovery entry point; the tests frame it that way and both crash-window subcases in `test_manual_inbox_recovery.py:98-139` now pin the replay invariants (event count, job count, leftover-copy cleanup).
- **Inference:** the fix suite closes the exact false-green holes from pass 1 — the uppercase-extension and matched-crash branches are now executed both by the three tests and by my independent probes.

## Risks, Gaps, And Verification Needs

**Residual findings (all P2):**

1. **P2-1 (current-task residual, fail-closed): blank-but-nonempty identifiers bypass the new typed guard.** `manual_inbox.py:785` checks truthiness, so `doi=" "`, `registry_identifiers=(" ",)` etc. slip past and raise raw `ValueError: 稳定标识的身份材料不能为空` from `stable_id` (`domain/ids.py:26-27`) instead of `RequestNotRequiredError`. **Repro (executed):** `create_request` with `registry_identifiers=(" ",)`, `doi=None`, `pmid=None` → `ValueError`; verified zero side effects (no ledger row, no inbox dir, list unchanged). **User impact:** none (the orchestrator catches `DownloadRequestError`/`ValueError` separately at worst; no persisted damage). **Minimal fix:** normalize `doi`/`pmid`/`registry_identifiers` with the `_not_blank` semantics before the guard, or catch the `ValueError` and re-raise as `RequestNotRequiredError`. **Regression:** `test_blank_identifier_request_rejected_typed`. Note the new regression test (`test_download_request_transitions.py:139-145`) only covers *truly empty* identifiers, i.e. narrower than the fix's own claim.
2. **P2-2 (UX boundary, not a 3.3 contract violation):** the user-facing list shows `放入：evidence/manual-inbox/download-request_<24hex>` — a machine-looking folder name. It is the one folder the user must target (created by `create_request`, so no user mkdir needed), and no backend *state* terms leak; whether to shorten/humanize it belongs to the Task 3.5/3.6 user-interaction surface.
3. **P2-3 (3.4+ boundary, unchanged from pass 1):** login/error marker detection is HTML-gated (`:443-447`); a hypothetical publisher PDF login page carrying the correct DOI+title fragment could pass. Fail-closed mitigation exists (identifier/title mismatch rejects most such pages); OCR-free scope makes this a Task 3.4+ item by design.

**Objections for Codex:** (a) accepting on "3 passed + 432 passed" would still have been under-evidence — the blank-identifier boundary shows the regression test under-covers its fix claim; the probes, not the suite, caught it. (b) `_append_re_extraction_job` compares records excluding `created_at` — correct, but it means replayed jobs silently keep the first timestamp; fine for receipts, worth a one-line comment for the 3.4 executor.

**Bounded question for Codex:** fold the one-line P2-1 typed-error fix into a Task 3.3 patch round, or defer to Task 3.5? Safe provisional path: defer — behavior is fail-closed with zero persisted side effects, and no user-visible path reaches it without an upstream orchestrator bug.

## Recommended Next Step

Accept Task 3.3. Optional micro-patch before or alongside Task 3.4: normalize blank identifiers before the `:785` guard and add the named one-line regression test; record P2-2/P2-3 ownership (3.5/3.6 and 3.4 respectively) in the plan.

## Verdict

PASS; P0=0; P1=0; P2=3
