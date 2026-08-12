You are Pi (Oh My Pi) continuing the same implementation worker session for Task 3.3. Codex has performed the first acceptance review and rejected the current implementation for material false-green and real-use defects. This is an authorized bounded repair round, not a new task and not final acceptance.

Hard boundaries:

- Work only inside `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`.
- Do not commit. Do not edit Trellis, context, review, metrics, prompt, runner report, accepted Task 3.1/3.2 source/tests, or any Task 3.4+ surface.
- You may modify only `src/ci_workflow/ingestion/manual_inbox.py`, `src/ci_workflow/ingestion/__init__.py`, `schemas/download-request.schema.json`, `package-manifest.json`, `tests/contract/test_package_manifest.py` if registration truly requires it, and the three exact planned Task 3.3 integration test files below. Remove the three wrongly named Task 3.3 test files after transferring legitimate coverage.
- Do not add dependencies, network access, OCR, report/UI work, or security tests. Path and no-overwrite checks here are user-data integrity behavior, not security scope.
- Runner-managed output path: `runs/pi_ci_phase3_task33_repair.md`. Never write it through tools.

Read these files only:

- `context/ci_phase3_task33_context.md`
- `docs/specs/competitive-intelligence-workflow-design-v1.2.md`
- `src/ci_workflow/ingestion/manual_inbox.py`
- `src/ci_workflow/ingestion/__init__.py`
- `src/ci_workflow/domain/enums.py`
- `src/ci_workflow/domain/evidence.py`
- `src/ci_workflow/domain/ids.py`
- `src/ci_workflow/gates/models.py`
- `src/ci_workflow/storage/event_store.py`
- `src/ci_workflow/storage/content_store.py`
- `src/ci_workflow/application/project_service.py`
- `schemas/download-request.schema.json`
- `policies/gates/A-v1.yaml`
- `policies/gates/B-v1.yaml`
- `policies/gates/C-v1.yaml`
- `package-manifest.json`
- `tests/contract/test_package_manifest.py`
- `tests/integration/test_manual_inbox_download_lifecycle.py`
- `tests/integration/test_manual_inbox_content_identification.py`
- `tests/integration/test_manual_inbox_idempotent_replay.py`

Repair every item below and add a deterministic regression inside the exact planned three-file suite:

1. Rename/restructure the tests to exactly:
   - `tests/integration/test_manual_inbox_recovery.py`
   - `tests/integration/test_user_filename_auto_rename.py`
   - `tests/integration/test_download_request_transitions.py`
   Delete the three invented filenames. The approved plan expects exactly one top-level test node per file and an exact result of `3 passed`; preserve the full subcase matrix inside those nodes/helpers rather than discarding coverage.
2. A request must create its unique project-relative inbox directory immediately and update one concise native-Chinese `logs/download_requests.md` list containing what is needed, why, original landing/attachment links, the one relative folder, and “无需重命名”. Cancelling/accepting updates that list without exposing enums/log language.
3. Add a real filesystem entry point that inventories the request's inbox directory and reads publisher filenames itself. Test by writing an arbitrarily named real file to that folder, then invoking the scanner with no caller-supplied filename/content. Zero files, temporary/hidden files, multiple possible matches, one valid plus invalid files, and a valid single match must have deterministic user-directed outcomes. Do not claim “automatic” based only on a bytes API.
4. Bind request identity to project/report/product-or-trial/document role/exact target title or identifier/attachment/gate units so two different documents or gaps for one trial never overwrite each other. Recreating an identical request must return the existing record without resetting state or changing timestamps; a same-ID drift must fail closed.
5. Bind every request to the actual `GateSpec` identity/fingerprint and validate every requested unit against that spec. All missing units must be `critical`; every B completion/disposition extension and every C statistical/design extension must be rejected as nonblocking even if a caller incorrectly labels it blocking. Also require explicit evidence that the requested document is expected to close the named critical gap; otherwise no user request is created.
6. Fix transition event identity for repeated download cycles: a genuinely new file after `needs_re_download -> awaiting_user` must create a new transition event without colliding with the first attempt; replay of the exact same attempt stays idempotent. Persist attempt/version material and test at least two bad downloads followed by a valid file.
7. Fix re-extraction job persistence: appending the second gap/request must preserve all prior jobs; identical replay adds none. Add a regression with at least two jobs and two requests.
8. Accept must persist `source_version_id`, canonical archive relative path and re-extraction job IDs on the accepted request and schema. State-dependent schema/model guards must reject `matched`/`accepted` records missing their required identity, digest and archive metadata.
9. Perform one atomic canonical rename/archive. The accepted library contains one canonical file only; the original filename exists only in metadata. Never move a second original-name copy into the library, never overwrite a different same-named file, and replay does not duplicate. The inbox copy is removed only after the canonical archive and event/state record can be recovered deterministically.
10. Validate claimed type against content and filename enough to stop false acceptance: `.pdf` cannot pass with HTML/plain bytes; PDF must have a valid PDF signature/parser result, and HTML error/login pages cannot pass as source files. Replace the fake “HTML bytes named .pdf” acceptance test with a genuine parseable PDF fixture (metadata may carry DOI/NCT/title) or a correctly named HTML fixture. Extract PDF metadata in addition to page text. Normalize NCT case and DOI case/trailing punctuation.
11. Do not require a supplement title to repeat a long main-publication title when exact unique identifiers are sufficient. Use deterministic confidence: an exact DOI is unique; DOI+trial ID is strong; one identifier plus a meaningful normalized title can be sufficient. Filename never contributes. Test a valid publisher supplement named arbitrarily whose internal title is merely “Supplementary appendix”, plus wrong/ambiguous cases.
12. Narrow login/error-page detection to actual page/error context. A legitimate scientific document containing phrases such as “measurement error” or “not found in subgroup” must not be quarantined merely for those words.
13. Quarantine must preserve each rejected file under a digest-disambiguated relative path, persist those paths/reasons, and never overwrite accepted content. User-visible instruction must be one clear native-Chinese action sentence. A later valid file must be able to recover the same request.
14. Ensure request persistence, download-list persistence and job persistence are atomic and preserve all existing records. No write may replace a multi-line ledger with only the newest record.

Verification and report:

- Run exact focused command and report exactly `3 passed`:
  `.venv/bin/pytest tests/integration/test_manual_inbox_recovery.py tests/integration/test_user_filename_auto_rename.py tests/integration/test_download_request_transitions.py -q -p no:cacheprovider`
- Also run Task 3.1/3.2 regression, full pytest, Ruff on changed Python/tests, strict mypy on `src/ci_workflow/ingestion`, JSON/schema/package verification, and `git diff --check`. Investigate any zero/empty count or unexpected outcome.
- Return `# Execution Manager Report: ci_phase3_task33_repair` with files changed, each defect and fix, exact test counts/commands, failed paths and diagnosis, remaining uncertainty, and Codex-owned next checks. Do not claim acceptance.

Also read and obey the latest global `/Users/smkzw/.codex/AGENTS.md`, workspace `AGENTS.md`, and `/Users/smkzw/.hermes/SOUL.md`; they are instruction sources, not evidence files.
