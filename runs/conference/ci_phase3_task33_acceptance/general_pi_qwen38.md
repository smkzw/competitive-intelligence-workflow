All anchors verified and both defect candidates reproduced live. Evidence is complete — composing the acceptance report.

# Conference Participant Output: ci_phase3_task33_acceptance - general_pi_qwen38

## Boundary Check

- Worked only inside `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow` (reads) plus probe scripts under `/tmp/ci_task33_probe/` (temp project roots created by `tempfile.mkdtemp`, deleted after). **No repo file written or modified**; `git status` unchanged by my pass.
- Read only the named source packet: `src/ci_workflow/ingestion/manual_inbox.py`, `schemas/download-request.schema.json`, `src/ci_workflow/ingestion/__init__.py`, `package-manifest.json`, `policies/gates/{A,B,C}-v1.yaml` (B read fully, A/C loaded in probes), `src/ci_workflow/gates/models.py`, the three integration tests, plus supporting truth sources (`event_store.py`, `content_store.py`, `enums.py`, `ids.py`, `classifier.py`, migrations, spec §10.2/§11.5/§11.7, `project_service.py`).
- Did **not** read `runs/conference/ci_phase3_task33_acceptance/general_grok45.md` or any other participant output. No production paths touched. Report returned as text for the runner to persist.

## Independent Work Product

**1. Exact three-file test command (re-run, not trusted):**
`uv run pytest tests/integration/test_manual_inbox_recovery.py tests/integration/test_user_filename_auto_rename.py tests/integration/test_download_request_transitions.py` → **`3 passed in 0.79s`** (each file contains exactly one top-level test node, as required). Full suite: **`432 passed in 12.30s`**. `ruff check` on changed files: clean. `mypy --strict` on `manual_inbox.py`: clean. `git diff --check`: clean. Codex anchors reproduce.

**2. Independent probe suite** (27 probes / 86 assertions + 6 focused repros, real temp-dir projects, real SQLite/JSONL/events on disk): verified happy chain, rule binding, normalization, quarantine, archive, ledgers, events, replay. Majority pass; two genuine defects and several minor issues found below.

**3. Findings.**

### P1-1 Uppercase-extension files are deterministically quarantined with a backend-term reason — violates "keep the original filename" contract

- **File/lines:** `src/ci_workflow/ingestion/manual_inbox.py:963` (`media_type = _media_type_for(filepath.suffix)` — case-preserving) + `:453-458` (lookup dict keyed lowercase only) + `:463-479` (`_validate_file_type` lowercases the extension, then demands the media type that the buggy lookup failed to produce).
- **Reproduction (executed):** create a request as in the tests, drop `SUPPLEMENT.HTML` containing matching NCT/DOI text into the inbox, `scan_and_process_inbox()`.
- **Actual:** state `needs_re_download`; `quarantine_reason_zh == "HTML 文件必须使用 text/html 媒体类型"`; identical bytes named `supplement.html` are accepted (control executed). Same for `.PDF`/`.TXT` uppercase.
- **Expected:** accepted; extension case is part of the publisher's original filename the user is told to keep ("用户保留原文件名", spec §11.7; task objective).
- **User impact:** a legitimate download with an uppercase extension can never be accepted through the documented scan path; the persisted Chinese reason leaks a backend concept ("媒体类型") and is not actionable — the user cannot fix it without renaming, which the contract says they never do. None of the three tests covers extension case, so the branch is unexecuted (false coverage).
- **Minimal fix:** `_media_type_for(filepath.suffix.lower())` at line 963 (or lowercase inside `_media_type_for`).
- **Suggested regression:** `test_inbox_extension_case_insensitive_acceptance` (uppercase `.HTML`/`.PDF` twins accepted identically).

### P1-2 Crash between `matched` and `accepted` wedges the documented scan recovery (idempotent continuation fails)

- **File/lines:** `manual_inbox.py:1081-1084` (`match_and_accept` raises unless state is exactly `FILE_DETECTED`) reached via `scan_and_process_inbox` `:995-1007`; `detect_file` no-op for same digest at `:867-875,916-917`.
- **Reproduction (executed):** `detect_file` → `match_file` (state `matched` persisted, file still in inbox — `accept` deletes the inbox copy only at `:1396-1398`), simulate crash, re-run the documented entry point `scan_and_process_inbox(rid)`.
- **Actual:** raises `UndeclaredTransitionError: 匹配只能在文件检测后执行（matched）`; request stuck in `matched`, file remains in inbox, download list still shows the request active; repeating the scan raises again. Only a developer-level direct `accept()` call recovers (verified).
- **Expected:** replay completes to `accepted` with no duplicated moves/events/jobs (task objective "幂等续跑"; spec §10.2 "重放同一事件不得重复…"; context challenge item "作业崩溃重放").
- **User impact:** after any process death in the matched→accepted window, the operator-visible recovery loop (rescan) fails closed forever; recovery requires an API call outside the documented user path.
- **Minimal fix:** in `match_and_accept`, treat `MATCHED` with identical `content_sha256` as already matched (mirroring the existing `ACCEPTED` early return at `:1079-1080`) and proceed to `accept()`; `matched -> accepted` is already a declared transition, so no table change.
- **Suggested regression:** `test_crash_replay_from_matched_completes_without_duplicates` (detect→match→rescan ⇒ accepted; jobs/events counts unchanged).

### P2 items

1. **Cross-run duplicate deadlocks the later run's inbox.** Same paper (same DOI/trial/title/attachment) requested in `run-A` and `run-B` yields two distinct request IDs (by-design per test `test_download_request_transitions.py:262-264`). Dropping the correct file into run-B's inbox quarantines it: "文件同时匹配多个下载请求，存在歧义，请按提示重新放入" (`manual_inbox.py:1143-1146`) — re-placing cannot resolve it; only cancelling run-A via `mark_not_required` (an orchestration action) unblocks. Fail-closed, but the reason text misdirects the user. Remediation: same-identity cross-run requests should deduplicate at creation or the collision reason must name the conflicting request; decide ownership (Task 3.3 guard vs Task 3.5 control chart).
2. **Untyped crash for identity-less requests.** `create_request` with no DOI/PMID/registry identifiers raises raw `ValueError: 稳定标识的身份材料不能为空` from `stable_id` (`manual_inbox.py:818-825` → `domain/ids.py:26-27`) instead of `RequestNotRequiredError`; such a request would be unmatchable anyway (`_match_guard` requires identifier intersection, `:1131-1135`). Remediation: reject with `RequestNotRequiredError` before ID computation.
3. **Quarantine note overwrite.** `处理说明.md` is rewritten on every quarantine (`:1059-1060`, `:1217-1218`), keeping only the last reason in the note file (full history survives in events/request record). Append or index notes per quarantined file.
4. **Empty-list copy drift.** `project_service.py:50` seeds "当前无需用户补充的文件。" while regeneration writes "当前无需补充资料。" (`manual_inbox.py:591`) — two writers, two wordings of the same user-facing file.
5. **Schema/model enforcement divergence.** `download-request.schema.json` `allOf` requires non-null `original_filename` for `accepted`; Pydantic `_accepted_requires_archive_metadata` (`:266-281`) does not enforce it (in practice always set via `detect_file`, but a hand-built `ACCEPTED` model passes Pydantic and fails the schema).

**Verified clean (evidence in probes):** real GateSpec binding incl. forged/altered-spec/wrong-kind/non-blocking/extension-unit/unknown-unit/gap-closed/non-covering rejections with zero persisted rows (P1.3); same-arg recreate is a true no-op (id, state, timestamps, ledger length); identity drift on same `request_id` fails closed; NCT case-folding + DOI trailing-punct + casefold normalization; wrong-attachment, NCT-only-without-title ambiguity, login/error page, unreadable binary all quarantined with Chinese reasons and inbox emptied; HTML-as-PDF and HTML-for-`publication_pdf` rejected while a real reportlab PDF is accepted; canonical name = slug(role)+digest, original filename only in metadata, library bytes digest-verified, source version + 4 date assertions + content blob in SQLite, one queued re-extraction job per missing gap; two bad rounds produce two distinct `needs_re_download` events with `attempt_number` increment and the exact 7-event chain; full replay after accept adds zero jobs/events (event stream re-validates); archive-drift pre-seed fails closed; all 34 persisted ledger records validate against the JSON Schema with ≥5 states exercised; download list has one entry per active request, contains "无需重命名", and leaks no backend terms (`awaiting_user`, `gate-spec`, `sha256`, …).

## Evidence And Assumptions

- **Evidence (directly executed/observed):** 3-file pytest `3 passed`; full suite `432 passed`; ruff/mypy/`git diff --check` clean; probe suite 86 assertions (6 initial failures triaged in focused repros: 2 confirmed defects, 4 probe artifacts or correct idempotent behavior — e.g. `detect_file` with identical content on `accepted` is a designed no-op, different content raises; `mark_not_required` early-return on `not_required` is correct replay semantics, not a gap-guard bypass).
- **Assumptions:** (a) `scan_and_process_inbox` is the intended operator recovery entry point after restart (it is the only filesystem-driven API and the tests frame it as "真实文件系统行为"); (b) cross-run request duplication is intentional identity design (anchored by the existing test), making P2-1 an orchestration-boundary issue; (c) `_LOGIN_OR_ERROR_MARKERS` being HTML-only is in scope — PDF login pages are a residual risk for Task 3.4+, not a 3.3 defect.
- **Inference:** the uppercase-extension and matched-crash branches are unexecuted by all 432 tests, which is why the anchors can be green while both defects exist — this is precisely the "false green" class the conference was convened to catch.

## Risks, Gaps, And Verification Needs

- P1-2's fix must be paired with a replay assertion (jobs/events/blob counts unchanged) so the new `MATCHED` fast path cannot reintroduce duplicate archiving.
- P2-1 needs a Codex decision: dedupe identical-document requests across runs at creation (changes `_request_id` semantics, conflicts with the existing cross-run test) vs keep the guard and require orchestration to cancel the stale run's request (Task 3.5 territory). Both are safe; silence is not.
- Not verified (out of scope per context): OCR-free extraction quality on real publisher PDFs, re-extraction job *execution* (jobs are receipts only in 3.3), Task 3.4+ control-chart consumption of these events.
- Title matching is CJK-only (`_title_fragments` splits on non-CJK runs, `:448-450`): English-only titles can never pass the NCT/PMID-only title check and always quarantine. Conservative and fail-closed, acceptable for 3.3, but worth recording before real-paper ingestion.

## Recommended Next Step

Do not accept Task 3.3 yet. Two bounded fixes: (1) lowercase the suffix feeding `_media_type_for` at `manual_inbox.py:963`; (2) let `match_and_accept` continue from `MATCHED` with identical digest into `accept()`. Add the two named regression tests (uppercase-extension acceptance; crash replay from `matched` with no duplicate effects), re-run the exact three-file command plus full suite, then re-convene. P2-1 should get an explicit Codex ownership decision (3.3 guard wording vs 3.5 dedupe) recorded in the plan.

**Objection to the initial posture:** the anchor "3 passed + 432 passed" is real but insufficient evidence for this task — the challenge list's "作业崩溃重放" and "保留原文件名" branches are not exercised anywhere in the suite; accepting on test counts would have shipped both P1s.

**Bounded question for Codex:** is cross-run duplication of identical download requests (P2-1) intended to be resolved by Task 3.5 orchestration, or should 3.3 itself dedupe same-document requests across runs? Safe provisional path: keep current fail-closed guard, fix only the misleading reason text, and assign dedupe to the control-chart task.

## Verdict

FAIL; P0=0; P1=2; P2=5
