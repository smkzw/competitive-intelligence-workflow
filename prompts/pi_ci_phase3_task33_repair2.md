Continue the same Pi/OMP Task 3.3 implementation session. Codex independently ran the exact suite (`3 passed`) but rejected it because direct source inspection and uncovered branch probes show P0/P1 false-green. This is the final narrow implementation repair; do not restart broad exploration and do not claim acceptance.

Hard boundaries are unchanged from the preceding repair round. Modify only the Task 3.3 source/schema/exact three tests/package exports already in scope. Do not commit or edit task records/reports. Runner-managed output path: `runs/pi_ci_phase3_task33_repair2.md`. Never write it through tools.

Read these files only:

- `context/ci_phase3_task33_context.md`
- `docs/specs/competitive-intelligence-workflow-design-v1.2.md`
- `src/ci_workflow/ingestion/manual_inbox.py`
- `src/ci_workflow/ingestion/__init__.py`
- `src/ci_workflow/domain/enums.py`
- `src/ci_workflow/gates/models.py`
- `src/ci_workflow/storage/event_store.py`
- `src/ci_workflow/storage/content_store.py`
- `schemas/download-request.schema.json`
- `policies/gates/A-v1.yaml`
- `policies/gates/B-v1.yaml`
- `policies/gates/C-v1.yaml`
- `tests/integration/test_manual_inbox_recovery.py`
- `tests/integration/test_user_filename_auto_rename.py`
- `tests/integration/test_download_request_transitions.py`

Close these exact findings with assertions in the existing three top-level nodes:

1. Delete caller-fabricated `GateSpecInput`. `create_request` must accept the real immutable `GateSpec` loaded from the approved YAML and validate `report_kind`, `spec_id`, real `spec_fingerprint`, and every requested unit's `blocking_level=critical`. Persist that actual identity. Tests must call `GateSpec.from_yaml`; fake fingerprints/critical lists must be impossible. A B spec for C, a modified/fake spec, `blocking_priority=non_blocking`, an extension unit, or unknown unit fails before any request/directory/list write.
2. Add explicit typed request guards proving (a) the critical gap is still open after accepted evidence and (b) this exact target document is expected to close at least one named critical unit. If either is false, no request is created. This is the mechanical form of “main/registry/regulatory material already sufficient means no supplement request”. Do not infer it from caller prose.
3. Request identity must include report, product/trial, document role, stable exact source identity (DOI/PMID/registry+title), attachment URL, sorted critical units and spec fingerprint. Identical creation returns the existing record unchanged (same state/timestamps, no duplicate list entry). A forced same-ID payload drift fails closed. Two documents for the same trial and same gap remain distinct.
4. Implement and event-log `needs_re_download -> awaiting_user`; persist an `attempt_number` (or equivalent) and include it in all transition event identities/guards. Two cycles using the same bad bytes/reason must still create distinct attempt events, while replay within one state/attempt stays idempotent. Every declared transition, including `not_required`, must use the same declared-transition guard path rather than bypassing it.
5. Fix the currently uncovered multi-file branch (it now passes an extra positional `request_id` and would raise `TypeError`). Scan every visible candidate: quarantine invalid/error files; if exactly one valid high-confidence target remains, accept it; if more than one valid target remains, quarantine all as ambiguous. A valid file plus one login page must recover without asking the user to delete both. Preserve each rejected file by digest.
6. Make content matching real and normalized. Normalize NCT to uppercase, DOI to casefold without terminal citation punctuation, and PMID forms. Exact unique DOI is sufficient; DOI+NCT is strong; NCT/PMID alone requires a meaningful normalized title match. Automatically compare against other active requests so one file cannot be silently accepted for two different target documents. The scanner must not rely on a caller-supplied candidate list.
7. Fix PDF support and role/type coherence. `_pdf_metadata` is currently unused and incorrectly calls `getattr` on a dict. Parse a genuine PDF, combine title/subject/keywords metadata with page text, and validate parser success. `publication_pdf` must require a real PDF; a `.html` file cannot satisfy it. All public paths (`scan`, `detect/match/accept`) must enforce filename/media/content coherence so the direct API cannot accept `text/plain` bytes named `.pdf` as the current transition test does. Replace that fake acceptance test.
8. Make job append idempotent and conflict-aware by stable `job_id`: identical retry is a no-op, same ID/different payload fails, and crash/replay after jobs but before final request state cannot duplicate. Verify canonical archive pre-existence by digest; never silently reuse drift. Model and JSON schema must enforce state-dependent requirements for both `matched` and `accepted`, including nonempty matched identifiers and job IDs plus project-relative canonical/quarantine paths.
9. Replace append-only status chatter in `logs/download_requests.md` with an atomically regenerated concise current download list from materialized requests: only active user-action requests, each once; accepted/not-required requests disappear; when none remain, state “当前无需补充资料”. Do not show raw states, `GateSpec`, checkmarks/crosses, prompts or log vocabulary. Preserve the original links, relative folder, reason and “无需重命名”.
10. Remove duplicate dead helpers (`_download_list_line` vs `_request_list_line`) and make claims in the execution report match executable behavior. Add a direct regression for every finding above, especially the previously unexecuted multi-file branch, identical-create non-reset, `re_request` event, fabricated spec rejection, direct API fake-PDF rejection, and crash-style duplicate job append.

Verification:

- Exact three files must remain exactly `3 passed`.
- Run Task 3.1/3.2 regression, full pytest, Ruff, strict mypy, schema/package checks and `git diff --check`.
- Report exact command/count evidence and any residual limitation. Do not say “all defects fixed” unless each numbered regression is present and executed.
- Output headings: `# Execution Manager Report: ci_phase3_task33_repair2`, `## Files Changed`, `## Findings Closed`, `## Exact Regression Mapping`, `## Verification`, `## Failed Paths And Diagnosis`, `## Residual Uncertainty`, `## Codex-Owned Next Step`.

Read and obey the latest global `/Users/smkzw/.codex/AGENTS.md`, workspace `AGENTS.md`, and `/Users/smkzw/.hermes/SOUL.md` as instruction sources.
