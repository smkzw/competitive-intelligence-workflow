I'll read the assigned execution context and plan first, then extract only the source-bound candidates those files authorize.The assignment is one candidate file from two native papers, using the existing fact and clause contracts. I'll read those contracts and the source leaves next.Contracts require exact JATS paths and production quotes. I'll pull only the two source-version leaves, then index the papers for primary outcomes and the scoped safety totals.Dupilumab primary cells and safety totals are located. Next I’ll read the nemolizumab long-term safety sections with the same path rules.The papers’ primary and safety cells are identified. I’ll replay them through the production quote function and write only `candidate.json` if every contract check passes.Quote replay works. I’ll build the candidate from those exact locators, validate every fact, and write the file only if the grouped check passes.# Execution Output: ci-1007-publication-atoms-v1 - worker_01

The candidate is written and contract-checked. It is not accepted science. File: `.artifacts/1007-publication-atoms-v1/candidate.json` (`proposal_not_accepted`, 109 facts, SHA-256 `ca1933e75aef9a8a726f05d3b6ccf11209030e8580f701313b04295736b61227`, 1,443,536 bytes). Codex still owns identity, numeric context, and any adoption.

## Boundary And Context Check

- Work stayed in the runner workspace. The only write is the exclusive create of that candidate. No report file, code, test, raw copy, database, or current/product path was written.
- Native bytes match the dated leaves. PMID 37142763 / `linked-jats-pmc10202800` / `source-version_97ae44d7c91576211da4b0fe` / raw `2bb91f3c0ec34d8aebf9a6c4bf879d866cc66d214f4fc5e6e81a59ec6992dd71` (172,525 bytes). PMID 41405008 / `linked-jats-pmc13308661` / `source-version_714c9a5ab64c8a4ab8e12890` / raw `5354b1ad692e3127692bc7d11a131558fa12f41f72d18001f37b034a1fe51cd0` (123,886 bytes).
- Fact `source_id` is the linked-JATS capture id. The PubMed record id and source-version id are in `source_set` for the same bytes. Both leaves still have `first_disclosed_at` not publicly disclosed. That was not treated as a first date.
- Contracts read: `ResearchFact`, `ResearchResultContext`, `SourceCapture` in `src/ci_workflow/application/source_research_service.py`; `SourceClauseContext` in `src/ci_workflow/domain/source_clause_context.py`; `extract_locator_quote` in `src/ci_workflow/storage/source_derivation.py`; `EvidenceLocator` / `source_version_identity` in `src/ci_workflow/domain/evidence.py`; linked-JATS identity in `src/ci_workflow/sources/connectors/linked_jats.py`. Checkpoint JSON was read only as source leaves, not its embedded raw XML.

## Work Performed

Both JATS articles were parsed from the raw bins. Quotes used production `extract_locator_quote` on `text/xml`. Each stored fact was reopened with `ResearchFact.model_validate_json`. One grouped replay then checked every fact and continuation path against the same bytes: 1,149 quotes matched.

Dupilumab, LIBERTY-PN PRIME and PRIME2, 47 facts:

- Primary endpoint is a ≥4-point WI-NRS reduction. Methods and results both say the original timepoint was week 12, and PRIME was moved to week 24 by amendment before database lock. Footnote a: week 24 is primary in PRIME and key secondary in “PRIME 2”. Footnote b: week 12 is primary in “PRIME 2” and secondary in PRIME.
- Extracted primary cells only. PRIME week 24: placebo `14 (18.4)`, dupilumab `45 (60.0)`, difference `42.7 (27.8 to 57.7)`, `<0.001 (1)`. PRIME2 week 12: placebo `18 (22.0)`, dupilumab `29 (37.2)`, difference `16.8 (2.3 to 31.2)`, `0.022 (1)`. The other study’s cells on those rows were not extracted as primary.
- Arm cells keep count and percent together. Column `n` is context, not a recalculated denominator. Difference and P cells have no `ResearchResultContext`, because they are not one arm.
- Safety table, 24 weeks of treatment, actual drug received: any TEAE, treatment-emergent SAE, deaths, and TEAE leading to discontinuation, four groups. Deaths are bare `0` in all four cells. Dupilumab discontinuation cells are `0`; placebo is `2 (2.7)` in PRIME and `1 (1.2)` in PRIME2.
- Efficacy column N is 76/75 and 82/78. Safety column N is 75/75 and 82/77. Both sets are stored. They are not merged.

Nemolizumab, OLYMPIA LTE, 62 facts:

- Table 2 is treatment-period safety for Nemolizumab Q4W, overall `N = 508`, not split by cohort. Time windows are `<12 months (N = 508)`, `12–<24 months (N = 409)`, and `≥24 months (N = 286)`.
- Scoped rows and their exposure-adjusted rates where the cell has text: any TEAE `452 (89)` / `197.49`; related TEAE `165 (32)` / `21.95`; serious TEAE `83 (16)` / `9.08`; related serious TEAE `7 (1)` / `0.70`; TEAE leading to trial discontinuation `44 (9)` / `4.41`; TEAE leading to death `1 (<1) b` / `0.10`. Later death cells are reported `0` for those windows only.
- Mild, moderate, and severe rows are included because the stated primary safety endpoint includes severity. Their exposure-adjusted cells are empty and are gaps, not zeros.
- Population text keeps 508 entrants, 307 continuous, 174 naive, 27 re-treatment, 290/508 through week 100, total PYE `1002.66`, and mean/median treatment `733 (839.5)` days inside one paragraph. Table 1 headers repeat 508, 307, and 174. No sum was created.

`result_context.trial_id` is the source label `PRIME`, `PRIME2`, or `OLYMPIA LTE`. No NCT was assigned. No Chinese drug name, MAH, cross-trial comparison, or clinical equivalence was written.

## Artifacts And Evidence

- Artifact: `.artifacts/1007-publication-atoms-v1/candidate.json`.
- Counts: dupilumab 13 definition, 2 narrative, 8 population, 8 primary-result, 16 safety-total. Nemolizumab 9 definition, 2 narrative, 9 population, 42 safety-total. Nineteen `missing_or_conflicting_scopes` entries.
- Material gaps, all with source paths in the file: NCT04183335 and NCT04202679 are co-listed only; `PRIME2` versus `PRIME 2`; efficacy versus safety column N; welded parent list quote `baselineto` was not used; no dupilumab all-cause discontinuation cell, related-TEAE total, death narrative, or text in image extended-data tables; ITT versus “full analysis set” not equated; phase 2a in results versus phase 2b `NCT03181503` in methods; re-treatment excluded from the manuscript in methods but included for safety in the figure note, while Table 2 has no cohort split; abstract EAIR `197.5` versus table `197.49`; prose `0.7` versus table `0.70`; trial discontinuation for AEs `51/508` versus TEAE leading to discontinuation `44 (9)`; follow-up death is prose and “data not shown”; AESI and preferred-term rows were seen and not cell-extracted; `NCT05052983` is a durability rollover note only.

## Commands And Observations

- `.venv/bin/python` read checkpoint top-level records and the two source-version leaves, omitting `content_text`. Observation: version ids, capture ids, hashes, and `exact_declared_epub_day_only`.
- `.venv/bin/python` plus ElementTree indexed both bins. Observation: SHA equals the filename; dupilumab Tables 2 and 3 have cells; Extended Data Tables are `graphic` only; nemolizumab Table 2 has the safety grid; three severity EAIR cells have no text.
- Production quote smoke test returned `45 (60.0)` for the PRIME dupilumab week-24 cell.
- The same interpreter built the candidate, validated every fact, replayed 1,149 locators, and created the file with exclusive `open(..., "x")`. Exit 0. No package install and no network call.

## Blockers Or Missing Environment

No environment blocker. The candidate was created. Image-only extended data and the disposition figure have no quoteable cells; that is source structure, not a missing tool.

Uncertainty for Codex: fact `source_id` follows `source_capture_from_linked_jats_xml` (`linked-jats-pmc...`). The dated `source_version_id` is stored on `pubmed-record-...` for the same hash. Both are in `source_set`. Severity rows were included as part of the stated nemolizumab primary safety endpoint; AESI line items were not.

## Rerun Requests Or Next Step

Codex can rerun the grouped `model_validate_json` plus `extract_locator_quote` audit on this frozen file. No worker rerun is needed unless Codex wants `fact.source_id` changed to the PubMed record id, or the severity rows removed before conference. Do not adopt these facts until that independent source review is complete.
