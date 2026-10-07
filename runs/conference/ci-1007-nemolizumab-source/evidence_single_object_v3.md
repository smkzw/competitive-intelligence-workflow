Follow-up pass on F1–F4. Reading the v3 manifest, source set, and updated production/test files.

v3 source set implements F1–F4 as described. Verifying all new frozen hashes first.

Shell PATH appears restricted in this pass. Probing environment and using Python for hashing instead.

All 9 manifest hashes match. Now reading the updated production module and test file (the F2/F3 changes).

Production module read: dedup is renderer-level with first-row retention; copy now says 关系记录日期 plus separate witness line. Reading the updated test file and owner v3 artifacts.

Owner artifacts read. Now the full v3 reopen/projection/markup probe against the frozen candidate.

Byte-level markup hash matches the owner exactly. One count to decompose (IL-31RA=2 could be target line + source quote), plus the two new tests.

Markup decomposition confirms dedup (1 target name in the target line; the second occurrence is inside the source quote). One audit-field observation found (unresolved duplicates). Now running the two new identity-copy cases.

All probes and the two new cases pass. Composing the final report.

# Conference Output: ci-1007-nemolizumab-source - evidence_single_object

## Output

**Verdict: bounded ACCEPT for the F1–F4 v3 corrections.** No counterexample falsifying any of the four adopted decisions was found; the v3 frozen unit is hash-consistent, source-faithful, and the rendered common markup was reproduced byte-for-byte against the owner's recorded HTML hash. One non-blocking audit-field observation (O1) and two presentation notes (N1/N2) are recorded below. This is advisory, same-session, reduced-independence review; not final acceptance, not browser/China/current-dynamic validation.

### 1. Hash and freeze verification (actual commands/results)

`shasum -a 256` over the 9 files in `.artifacts/1007-nemolizumab-review-v2/MANIFEST.json` — all match sha256 and byte size:

| File | sha256 (prefix) | bytes |
|---|---|---|
| `src/ci_workflow/reports/common/identity_projection.py` | `694f15c0…` | 21,273 |
| `src/ci_workflow/sources/connectors/public_pdf_availability.py` | `10b42863…` (unchanged from v2) | 17,235 |
| `tests/integration/test_1007_identity_projection.py` | `65b184cf…` | 15,778 |
| `tests/integration/test_r24_public_pdf_availability.py` | `1fa30e76…` (unchanged) | 13,539 |
| `tools/materialize_identity_sources.py` | `7ae56113…` (unchanged) | 9,360 |
| `…identity-source-set-v3.json` | `00d04654…` | 19,841 |
| `owner-nemolizumab-identity-materialize-v3.json` | `3a1741d7…` | 760 |
| `owner-nemolizumab-identity-projection-v3.json` | `f3112ee2…` | 13,052 |
| `owner-identity-copy-green-v1.txt` | `b672da83…` | 179 |

The manifest's `previous_manifest_sha256` claim was also checked: `.artifacts/1007-nemolizumab-review-v1/MANIFEST.json` hashes to `142ac8ca…` — exact match. Candidate root `.artifacts/1007-nemolizumab-identity-candidate-v3` contains 12 CAS assets (3 source PDFs, 3 witness receipts, graph asset `562d9519…` = 13,781 B, 5 page-text derivations) + `identity-checkpoint.json` (source-set sha `00d04654…`, 7 fragments, 7 witnesses, `science_accepted:false`, `current_promoted:false`).

### 2. F1 — definition paragraph retained as context, not a control fact: VERIFIED

Reopened the v3 graph payload and DB:
- 4 entities, **6 relations** (v2 had 7), 7 `source_fragment_ids`, 7 witnesses.
- Relations: 2× `has_mah` (us_license, us_scope), 2× `controlled_by` (**group_row `00f7b750` + group_control_scope `0efaefeb`, i.e. exactly the two physical141 proofs**), 2× `has_target`.
- `evidence-fragment_34a95f7b…` (page-106 §1.2 definition) is **not referenced by any relation**, but **is retained**: present in `source_fragment_ids`, in the SQLite `evidence_fragments` table (DB count 7), and re-verified by the production reopen. The projected source list drops to 6; the definition quote does not appear in rendered markup.
- No new claims: substring `EQT` absent from the whole payload; the controlled_by scope states `截至2025-12-31财报合并范围…集团定义片段仅是上下文；不证明2026-10-07动态控股状态`; no CN jurisdiction and no China-negative claim (`current_China_status: unknown_not_negative`).

### 3. F2 — all `observed_at` = exact pinned witness times: VERIFIED

Equality check over all 6 relations: each relation's `observed_at` **exactly equals** the `observed_available_at` of its own fragment's witness:
- both `has_mah` → `2026-10-07T12:28:05.046284Z` (licence-letter GET); both `controlled_by` → `2026-10-07T12:28:06.708538Z` (AR GET); both `has_target` → `2026-10-07T12:28:06.672448Z` (label GET). Result: `True`.
- Legacy dates retained, not rewritten: v3 declares `previous_unaccepted_source_set_sha256 = bd35253d…` (the v2 set; v1 `cc1fb9fd…` was hash-verified in the prior pass holding the unjustified `2025-06-01`). `date_correction` states the v3 rule (approval signature is not a separate claim; unknown first-publication never backfilled).
- Copy: rendered markup contains `关系记录日期（含义见范围）` and the legacy ` · 观察于` label is absent; genuine witness time is separately rendered as `本次公开可得核查 <timestamp>` (6 lines, distribution 2/2/2 across the three witness instants).

Production probes (real candidate, read-only, `load_identity_context` reopen reverified all 7 raw→page-text→quote derivation chains):
- **current cutoff**: `公司：Galderma Group AG｜境外MAH所属集团（US）`; 2 data companies / 2 targets / 6 sources / 0 unresolved.
- **pre-witness cutoff** `2026-10-07T12:28:05.000Z`: `公司归属待核`, 0 companies, 0 targets, all relations `not_known_at_cutoff`.
- **holder-only cutoff** `2026-10-07T12:28:06.000Z`: `公司：Galderma Laboratories, L.P.｜境外MAH（US）`, group suppressed (`group_entity_id: None`), 2 sources (both licence-letter fragments), 0 targets.

No full-indications or latest-label acceptance is present: scope still bounds to `成人结节性痒疹` on the 2024 letter and `2025-06` label month with no invented first/effective day.

### 4. F3 — display dedup with full proof preservation: VERIFIED

New renderer logic inspected in `identity_projection.py:344-398`: companies keyed on (legal_entity_id, group_entity_id, role, jurisdiction, authorization_scope, effective_from/until, observed_at) with `setdefault`; group relations keyed similarly; targets deduped by `entity_id` via the Jinja `unique` filter. Projection data is untouched.

Independent markup probe of the **real v3 current projection** through the production renderer:
- `html sha256 = cddbfb29be9b6231ba2e064d41a8b1b54efbf7005318d2f0ce6ef2e9a0b0cab5` — **byte-identical to the owner artifact's `html_sha256`**.
- Counts: `持有人法律实体` = 1 (2 data rows collapsed), `集团关系范围` = 1 (2 collapsed), target `<dd>` line contains exactly 1 `IL-31RA` (the second occurrence in the file is inside the page-8 source quote, not a display duplication), scope text `截至2025-12-31财报合并范围` rendered once.
- Proof preservation: `<blockquote>` count = 6 = `len(sources)`; all 6 projected source quotes present in the HTML; the page-106 definition quote intentionally absent (F1).
- Distinct scopes preserved: ran the two new cases only — `test_identity_header_deduplicates_display_not_source_evidence` and `test_identity_header_keeps_distinct_authorization_scopes` — **2 passed** (`pytest -k`, 18 deselected, 0.23s). Owner `88 passed` green file treated as evidence, not my execution; no full 7-module rerun per instruction.
- Safety escaping: `autoescape=True` retained; in-memory probes injecting `<script>alert("x")</script>` into a scope and `<img …>` into a target name render escaped (`&lt;script&gt;` present, raw tags absent).

### 5. F4 — witness-count semantics: VERIFIED

v3 source set carries `witness_count_semantics: "3 distinct exact-byte GET receipts bind 7 source fragments; not 7 independent fetches."` Confirmed against the payload: 7 fragment-bound witnesses, 3 unique request URLs (AR ×3, licence letter ×2, label ×2), 3 unique receipt assets. Owner artifact records `unique_public_gets: 3, fragment_witnesses: 7`.

### 6. Observations and notes (non-blocking)

- **O1 (audit-field counterexample, lowest severity):** at the holder-only cutoff, `unresolved_relations` returns **6 raw entries for 4 unique relation ids** — the 2 stale `controlled_by` relations are appended once per passing `has_mah` edge (`group_chain` is invoked per has_mah row, `identity_projection.py:116-120`). Not rendered anywhere in the common markup, absent at the owner's 2026-03-01 snapshot (4 unique entries) and empty at current cutoff; it can only double-count if a future consumer counts raw entries. Consistent with the F3 decision to leave projection data unchanged; flagging as a bounded follow-up candidate, not a blocker.
- **N1:** rendered relationship/witness timestamps are raw ISO-8601 with microseconds inside Chinese copy (`2026-10-07T12:28:05.046284Z`). Codex owns the visual pass (NOT_RUN here); formatting is a presentation choice.
- **N2:** the group-first label `Galderma Group AG｜境外MAH所属集团（US）` is unchanged and was not reopened, per the explicit D1 decision; the legal holder remains preserved as `legal_entity_name` and the fail-closed fallback (`Galderma Laboratories, L.P.｜境外MAH（US）`) was exercised at the holder-only cutoff.
- Owner `probe_incident` (bs4 unavailable during their markup helper; stdlib fallback disclosed, no dependency installed): **does not affect the artifact** — my independent reproduction via the production Jinja renderer matches their `html_sha256` byte-for-byte.

### 7. Limitations

- NOT_RUN per assignment: browser/render acceptance, China approval status, current dynamic control/release, latest-label acceptance, full report render, visual/formatting acceptance.
- Same-session, reduced context independence is explicit; the 7-module/88-test owner run is evidence accepted as-is (not re-executed); only the two new copy cases were executed by me, plus real-candidate production reopen/projection/markup probes.
- The v1→v2→v3 unaccepted chain was verified by hash and declared fields; individual v2 dates were not re-litigated beyond the retained `previous_unaccepted` link.

No files were written in this pass; the runner-managed report path was not touched. Report returned as text for the runner.
