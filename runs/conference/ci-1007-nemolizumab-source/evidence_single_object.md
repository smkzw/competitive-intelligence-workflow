Trellis SessionStart context loaded. Proceeding with the bounded source identity review.

Initial read set loaded. Now verifying the frozen manifest hashes and inspecting production sources.

All 14 manifest file hashes match exactly. Now verifying the 3 raw PDFs.

All 3 raw PDF hashes match. Now extracting the actual PDF page texts to compare against the 7 claimed fragments.

pypdf available. Extracting actual page text from all three source PDFs.

FDA licence letter and label pages verify. Now the Galderma annual report pages 106 and 141 (26 MB PDF).

Pages extracted. Now checking the licence letter date (last page) and the label revision date for the public-knowledge date audit.

Licence letter signed 08/12/2024 (matches claimed 2024-08-12), label Revised 06/2025 (month-precision claim confirmed). Now reading the production sources and the candidate projection artifacts.

Now reading the domain entities, availability connector, and the two frozen tests.

Now reading the source-derivation helpers (quote extraction/verification) and both frozen tests.

Tests reference a `test_1007_identity_public_knowledge` module. Finding the freeze-adjacent test module list (7 modules).

Locating the freeze-adjacent list in the owner artifacts and reading them.

Candidate projection artifact inspected. Now verifying the candidate CAS root, graph asset, and witness receipts.

Canonical library file absent as expected (candidate mode). Checking CAS completeness for the source PDFs and DB.

Now running the actual production-function probes against the frozen candidate root.

Production probes pass at all three cutoffs. Now running the 7 freeze-adjacent test modules in the background while I inspect the remaining owner artifacts.

Owner green evidence shows 86 passed. Running the same 7 modules myself in the foreground, and reading the red host-negative artifact in parallel.

My run matches the owner's green evidence exactly (86 passed), and the red artifact shows the pre-fix failures the tests discriminate. Now checking the reopen verifier and date semantics internals.

Checking the repository-level reopen verification and dumping the SQLite fragment rows.

All fragment quotes and locators verify against raw bytes. Skimming the four remaining identity test modules for coverage characterization.

Two final checks: v1 source-set retention and witness cardinality (unique GETs vs fragment witnesses).

All cross-checks pass. One final end-to-end probe: re-running the production `materialize()` on the real pinned inputs into a fresh scratch directory to close the source-set→quote loop.

Replay is bit-for-bit reproducible (same graph asset hash). One last precision check on the retained v1 source set.

All checks complete. The v1 retention is exact (hash `cc1fb9fd…` = v2's declared previous set; v1 target date was indeed the unjustified `2025-06-01`). Composing the final report.

# Conference Output: ci-1007-nemolizumab-source - evidence_single_object

## Output

**Verdict: ACCEPT (bounded, advisory).** No blocking source-identity defect found in the frozen unit. All manifest hashes, all seven source fragments, all witness receipts, the production reopen/projection behavior, the seven freeze-adjacent test modules, and an end-to-end re-materialization from the pinned inputs were independently reproduced. Two recommended revisions (F1, F2) should be decided by Codex before this identity unit feeds user-facing copy. This is not final acceptance, not a repair, and not a global/clinical/browser pass.

### 1. What was independently verified (evidence)

All commands ran from the authorized workspace; only `.artifacts/ci-1007-source-conference-scratch/v2-replay` was created (fresh scratch, retained as evidence trail). No frozen input, candidate, DB, or source file was modified.

1. **Hash freeze.** All 14 manifest files match sha256 and byte size exactly (sources, tests, owner run artifacts, checkpoint). All 3 raw PDFs in `.artifacts/1007-nemolizumab-official-source-v1` match pinned sha256/size (`2337bb6e…` 3,232,946 B; `5b4bbacf…` 26,036,393 B; `9a50b06f…` 1,274,683 B). Candidate graph asset `6125f936…` (13,877 B) and all 3 witness receipts (`3f151b5b…`, `73cbcc5b…`, `dd40b121…`) hash-verify at their CAS paths.
2. **Quote verification against original PDFs** (pypdf 6.15.0, same version stored in the derivation receipts): all 7 fragments appear verbatim on their cited pages — licence letter page 1 (license 2289 + Nemluvio/nemolizumab-ilto/PN scope), Galderma AR pages 141 (LP table row, §3.2 indirect-control sentence) and 106 (§1.2 Group definition), label pages 8 (§11 DESCRIPTION) and 9 (§12.1 MOA). Only whitespace/line-break normalization; the `nemolizumab-i lto` spacing artifact in the `us_scope` quote is faithful to the extractor output, not a hand edit.
3. **Public-knowledge dates.** Licence letter electronic signature page (page 7): `/s/ KATHLEEN M DONOHUE 08/12/2024 04:52:16 PM` — supports the claimed `2024-08-12`. Label page 1: `Initial U.S. Approval: 2024`, recent-major-changes `06/2025`; page 20: `Revised: 06/2025` — supports month-precision `2025-06`. The retained v1 set hashes to `cc1fb9fd…` (exactly v2's declared previous set) and its `has_target observed_at` is the unjustified `2025-06-01`; v2 replaces it with the actual witness timestamp. The `date_correction` note is accurate.
4. **Production reopen + projection probes** (real candidate root, read-only):
   - `load_identity_context` reverified all 7 derivation chains (raw PDF → page text → locator quote) and all 7 witnesses (receipt reopen, exact bytes, URL admission) with a live clock.
   - Cutoff = now: `company_label = 公司：Galderma Group AG｜境外MAH所属集团（US）`; legal entity `Galderma Laboratories, L.P.` preserved; 2 target rows (IL-31RA); 7 sources; 0 unresolved.
   - Cutoff between licence witness (12:28:05.046284Z) and group/label witnesses (12:28:06.7Z): group claim suppressed; label becomes `公司：Galderma Laboratories, L.P.｜境外MAH（US）`; targets empty; 5 unresolved `not_known_at_cutoff`. This demonstrates the fail-closed group chain on the real artifact.
   - Cutoff before all witnesses: `公司归属待核`, 0 companies, 0 targets, 4 unresolved — matches the owner's historical projection exactly.
5. **Tests.** The 7 freeze-adjacent modules (`test_r24_public_pdf_availability`, `test_r24_public_pdf_current_ingestion`, `test_1007_identity_projection`, `test_1007_identity_public_knowledge`, `test_1007_identity_source_replay`, `test_1007_identity_consumers`, `test_1007_identity_fresh_context`): **86 passed in 2.61s**, identical to the owner green evidence (86 passed, 2.62s). The red artifact shows the same suite failing 4 discriminating tests when the host admission and group-label extension are absent — the tests are load-bearing, not vacuous.
6. **End-to-end replay.** `materialize()` (frozen production tool) run on the pinned source set + pinned source root into a fresh scratch dir reproduced the **same graph asset sha256 `6125f936…`**, all 7 fragment quotes byte-identical, reopen and projection identical. The frozen candidate is fully reproducible from pinned inputs and code.
7. **Boundary checks.** Exactly 3 official HTTPS GETs (FDA licence letter, FDA combined label with `%2C` path, Galderma AR) back 7 fragment-bound witnesses; request URL == final URL (no redirect), no query/fragment/credentials/port; all hosts in the admitted set; `published_at`/`first_disclosed_at` remain `not_publicly_disclosed` so the current observation can never backdate availability; receipt forgery/tamper/backdating paths fail closed in code and tests.
8. **Identity neutrality.** No `official_chinese_name` anywhere; China status `unknown_not_negative`; no `sponsored_by`→MAH inference; target is IL-31RA receptor, not the IL-31 cytokine; `ilto` suffix only as alias; entity basis strings are not name-derived.

### 2. Findings and proposed remediation (actionable, non-blocking)

**F1 — Medium: the page-106 §1.2 definition fragment is attached to a `controlled_by` relation it does not prove.** The quote ("These consolidated financial statements … comprise Galderma Group AG …") contains no LP reference and no control statement; the LP→Group control fact is actually proven by the two page-141 fragments (table row + §3.2 sentence), which are exact. Effects: strict fragment-by-fragment traceability fails for that one edge; the common header triple-renders "集团关系范围" rows; the group chain additionally requires this fragment to stay verifiable (fail-closed, so not a safety risk). *Alternative:* keep the claim and either re-scope that relation as Group-definition context (authorization_scope should say what the fragment proves), or cite §1.1's "became the parent entity of Galderma Holding SA and of all its controlled entities" — noting that even §1.1 needs the page-141 row to tie in the LP. Codex decision.

**F2 — Medium: `observed_at` mixes three semantics in one field that the renderer prints as "观察于".** `has_mah` = 2024-08-12 (documentary signature date; **not present in any fragment proof** — I confirmed it only from page 7 of the same pinned PDF), `controlled_by` = 2025-12-31T23:59:59 (fiscal as-of), `has_target` = 2026-10-07 actual witness time (documented in its scope). With v1's manufactured `2025-06-01` removed for the target row, the same class of issue persists for the other two rows. *Proposed:* either normalize `observed_at` to observation/acquire time and move documentary dates into `authorization_scope` (note: this changes cutoff behavior — the holder row would disappear at pre-witness cutoffs), or keep the dates and change user-facing wording to distinguish 事实日期 from 观察时间; and if 2024-08-12 remains a claim, consider materializing the page-7 signature block as a fragment.

**F3 — Low: duplicate presentation rows.** Two `has_mah` edges produce two identical company rows; two `has_target` edges make the renderer join "IL-31RA；IL-31RA". Dedup display only, keep evidence lists intact.

**F4 — Low, records precision:** the context phrase "7 actual same-byte public GET witnesses" is really **3 GETs → 7 fragment-bound witness records** (2/2/3). Audit wording should say 3 exact-byte GETs.

**F5 — Informational:** "境外MAH（US）" is Chinese convention; the source term is licensee ("U.S. License No. 2289 to Galderma Laboratories, L.P.") / BLA holder. The license number stays visible; flag only for copy review.

**F6 — Informational:** `us_scope` is correctly bounded to BLA 761390/Original 1 (adult PN); the June-2025 label adds atopic dermatitis. Ensure downstream copy does not read "US indications = PN only" from this unit. Also the `2025-06` month is only verifiable on label pages 1/20, which are not among the frozen fragments.

**F7 — Question:** the context describes physical106 as "Company definition/control change", but the frozen fragment carries only the §1.2 definition. The control-change narrative (2024-03-21 reorganization, 2024-03-22 IPO, 2025-03 Shareholder sale, "not controlled by any party" at 2025-12-31) is on the same pinned page but unmaterialized. Nothing in the unit asserts it — safe today; confirm intent.

### 3. Assumptions challenged / objections raised

- "7 witnesses" vs 3 GETs (F4) — an evidence-audit count, not a rounding nicety.
- "观察于 observed_at" blurs fact dates and observation times (F2); the field gates correctly in code, but user-facing copy can misread it.
- Page-106 fragment as control evidence (F1) — the aggregate claim survives on page 141 alone; the third edge adds fragility and a loose fragment→claim pairing.
- The group-first headline ("Galderma Group AG｜境外MAH所属集团（US）") leads with the group while D1 emphasizes the actual legal holder; the LP is preserved in `legal_entity_name` and the detail row, and the mid-cutoff probe shows the ungrouped fallback works. Confirm this is the intended audience-facing form (Codex owns user-facing calls).
- Two asserted dates (2024-08-12, 2025-06) are true but not self-proving inside the frozen fragment set; they are verifiable from the pinned bytes.

### 4. Bounded questions for Codex

1. Page 106: definition anchor only, or should the control-change narrative carry a user-facing claim? (If the latter, the unit needs an added fragment; currently nothing asserts it.)
2. Accept the `observed_at` semantic divergence for user-facing rendering, or normalize it? (If normalized, confirm the resulting pre-witness cutoff behavior change is acceptable.)
3. Should the "3 GETs / 7 witnesses" wording correction propagate to audit text?
4. Are the duplicate company/target render rows (F3) accepted as-is, or deduped at presentation?
5. Is the group-first company headline the intended form for senior clinical-trial medical professionals, given D1's emphasis on the actual legal holder?

### 5. Remaining uncertainty and limits

- Out of scope and untested here: browser/render acceptance, full-suite run, PDF/PPT, current China/US dynamic release, final clinical wording, visual acceptance, downstream report templates.
- pypdf extractor-version coupling is by design fail-closed: derivations pin `extractor_version 6.15.0`; any environment change forces re-materialization rather than silent drift. Operational note, not a defect.
- Whether any consumer projects at a cutoff between document dates and witness dates (the mid-cutoff path I exercised) is unknown; its behavior is safe and fallback-correct.
- The v1 set was verified as retained and hash-identified; I did not diff the full v1 corpus.
- No owner PASS prose was relied on; every conclusion above comes from re-executed checks. Nothing was written to `runs/conference/...`; the only new path is the scratch replay directory named in section 1.
