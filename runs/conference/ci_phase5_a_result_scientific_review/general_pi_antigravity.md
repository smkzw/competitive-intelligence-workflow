# Conference Participant Output: ci_phase5_a_result_scientific_review - general_pi_antigravity

## Boundary Check

1. **Working Directory & Role Boundary**:
   - Executed inside the authorized repository workspace without accessing production files outside the designated scope.
   - Verified that no source code, data artifacts, or production files were modified (`review-only` mode strictly maintained).
   - Report path `runs/conference/ci_phase5_a_result_scientific_review/general_pi_antigravity.md` was not written via tools; full findings are returned for runner persistence.
2. **Evidence & Network Policy**:
   - No external network calls were made. Source of truth remained the locked local package (`.artifacts/a-fresh-source/evidence/library/a-research-package.json`), rebuilt candidate (`.artifacts/a-atopic-dermatitis-rebuild/research-content.json`), deterministic manifest (`.artifacts/a-atopic-dermatitis-rebuild/rebuild-manifest.json`), extraction pipeline (`tools/rebuild_atopic_dermatitis_package.py`), domain model/audit services (`src/ci_workflow/application/source_research_service.py`), and focused integration tests (`tests/integration/test_atopic_dermatitis_package_rebuild.py` and `tests/integration/test_ctgov_result_coverage_audit.py`).
3. **Execution-Conference Deduplication**:
   - Operating as Participant 1 under independent execution, using `pi` / `google-antigravity` / `gemini-3.7-flash` (effort `high`). Excluded model nodes (`codex/gpt-5.6-luna`) respected.

---

## Independent Work Product

### 1. Scientific Verification Verdict: **ACCEPTED**

The rebuilt research candidate (`.artifacts/a-atopic-dermatitis-rebuild/research-content.json`) and manifest (`.artifacts/a-atopic-dermatitis-rebuild/rebuild-manifest.json`) strictly satisfy all scientific, coverage, semantic, and mathematical criteria:

- **Coverage Completeness**: 100% of safely parseable ClinicalTrials.gov results from all 17 completed/result-reporting trials (out of 43 registry sources) are fully captured with 0 missing outcomes, 0 missing AEs, and 0 parse failures.
- **Deterministic Rebuild Stability**: Byte-level determinism confirmed (`content_sha256: ef7522720682dcc70c78bb3251d58d35676626b9edb1d982d8041042fb6581ea`, `content_digest: 246e5116739711d070dbcbe1062f98c82b3c2fa78ae395a389931510b2073f2f`).
- **Mathematical Accuracy**: Zero percentage values exceed 100.0%. Zero divisions by zero occurred. All 10,046 numerator/denominator safety rows strictly match half-up rounded rate conversions without fabrication.
- **Semantic Differentiation**:
  - `otherNumAffected` is strictly prevented from being aliased as `任何TEAE`.
  - Common AEs are not projected as `AESI`.
  - Missing or non-estimable fields (e.g. median time "NA") and zero-risk denominators (`numAtRisk == 0`) are explicitly classified as `not_reported` in the manifest and never fabricated as `0%`.
  - `arm` ("治疗组" vs "对照组") and `arm_detail` (exact regimen title) are separately preserved across all 6,755 efficacy rows and 10,173 safety rows.

---

### 2. Deterministic Count & Metric Reproduction

| Entity / Metric | Locked Baseline | Rebuilt Candidate | Rebuild Delta | Independent Audit Verification |
| :--- | :--- | :--- | :--- | :--- |
| **Products** | 38 | 38 | 0 | Exactly 38 products, universe closed |
| **Trials** | 43 | 43 | 0 | Exactly 43 trials (17 with resultsSection, 26 without) |
| **Sources** | 65 | 65 | 0 | 65 locked sources (43 CTGov registries + 22 FDA/literature) |
| **Facts** | 45 | 17,009 | +16,964 | 16,840 rebuilt facts, 100% resolve cleanly to source JSON |
| **Claims** | 45 | 45 | 0 | 45 claims referencing valid fact subsets |
| **Efficacy Rows** | 10 | 6,755 | +6,745 | 6,745 rebuilt outcome values from CTGov |
| **Safety Rows** | 78 | 10,173 | +10,095 | 34 TEAE + 3,956 SAE + 0 AESI + 6,105 Common AE |
| **Explicit Not-Reported Values** | 0 | 10 | +10 | 3 'NA' measurements + 7 'numAtRisk == 0' event stats |
| **Parse Failures** | 0 | 0 | 0 | 0 parse failures |
| **Unmapped Sources** | 0 | 0 | 0 | 0 unmapped sources |

---

### 3. Exact High-Risk Conversion Verification

All specified high-risk rate conversions were independently located in the candidate and matched against raw source JSON nodes:

1. **411 / 602 $\rightarrow$ 68.3%**:
   - **Row ID**: `a-rebuild-safety-row_36a4e0f929e3f53fa015abf3`
   - **Trial / Product**: `NCT03131648` / `tralokinumab`
   - **Arm / Arm Detail**: `治疗组` / `Tralokinumab 300 mg Q2W`
   - **Category / Term**: `严重不良事件` / `任何SAE`
   - **Numerator / Denominator**: `411` / `602` $\rightarrow$ `68.2724%` $\rightarrow$ **`68.3%`**
   - **Fact / Locator**: `a-rebuild-fact_640440a2defab80bc6c3441f` $\rightarrow$ `ctgov-nct03131648` at `resultsSection.outcomeMeasuresModule.outcomeMeasures[7].classes[0].categories[0].measurements[0]`
   - **Raw Source Node**: `{'groupId': 'OG000', 'value': '411'}`

2. **133 / 196 $\rightarrow$ 67.9%**:
   - **Row ID**: `a-rebuild-safety-row_c0a1ad1bf9a46defdc0bef71`
   - **Trial / Product**: `NCT03131648` / `tralokinumab`
   - **Arm / Arm Detail**: `对照组` / `Placebo Q2W`
   - **Category / Term**: `严重不良事件` / `任何SAE`
   - **Numerator / Denominator**: `133` / `196` $\rightarrow$ `67.8571%` $\rightarrow$ **`67.9%`**
   - **Fact / Locator**: `a-rebuild-fact_2c050f377761e4ba58cd53b0` $\rightarrow$ `ctgov-nct03131648` at `resultsSection.outcomeMeasuresModule.outcomeMeasures[7].classes[0].categories[0].measurements[1]`
   - **Raw Source Node**: `{'groupId': 'OG001', 'value': '133'}`

3. **150 / 510 $\rightarrow$ 29.4%**:
   - **Row ID**: `a-rebuild-safety-row_a5637f0550ad3a33657d8c43`
   - **Trial / Product**: `NCT02118792` / `crisaborole`
   - **Arm / Arm Detail**: `治疗组` / `AN2728 Ointment, 2 Percent (%)`
   - **Category / Term**: `治疗期间不良事件` / `任何TEAE`
   - **Numerator / Denominator**: `150` / `510` $\rightarrow$ `29.4117%` $\rightarrow$ **`29.4%`**
   - **Fact / Locator**: `a-rebuild-fact_7ee5313d51c89f1193e18966` $\rightarrow$ `ctgov-nct02118792` at `resultsSection.outcomeMeasuresModule.outcomeMeasures[1].classes[0].categories[0].measurements[0]`
   - **Raw Source Node**: `{'groupId': 'OG000', 'value': '150'}`

---

### 4. Sampled Deep-Audit Across Data Categories

1. **Outcome / Efficacy Sample**:
   - `Row ID`: `a-rebuild-efficacy-row_0015da177fccad72fa7db9fc` (`NCT05131477`, `amlitelimab`)
   - `Endpoint / Timepoint`: `Percentage Change From Baseline in EASI (Part 2) (Week 24)` / `Baseline to weeks 24, 28, 32, 36, 40, 44, 48, & 52`
   - `Arm / Arm Detail`: `对照组` / `Placebo Re-randomized From the 62.5 mg Arm (Part 2)`
   - `Value / Unit`: `-76.74 %` | `Population`: FAS2 population text preserved verbatim.
   - `Locator`: `resultsSection.outcomeMeasuresModule.outcomeMeasures[9].classes[0].categories[0].measurements[7]`
2. **TEAE Sample**:
   - `Row ID`: `a-rebuild-safety-row_0b1cd29fda2e7759d4d3b216` (`NCT03533751`, `etokimab`)
   - `Term / Category`: `任何TEAE` / `治疗期间不良事件`
   - `Arm / Arm Detail`: `治疗组` / `Etokimab 300 mg / 150 mg SC Q4W`
   - `Numerator / Denominator / Rate`: `42` / `60` $\rightarrow$ `70.0%`
   - `Locator`: `resultsSection.outcomeMeasuresModule.outcomeMeasures[10].classes[0].categories[0].measurements[3]`
3. **SAE Sample**:
   - `Row ID`: `a-rebuild-safety-row_00140e24b628d2bb5f0b404d` (`NCT03809663`, `tezepelumab`)
   - `Term / Category`: `任何SAE` / `严重不良事件`
   - `Arm / Arm Detail`: `对照组` / `Placebo- Tezepelumab 420 mg Q2W`
   - `Numerator / Denominator / Rate`: `2` / `39` $\rightarrow$ `5.1%`
   - `Locator`: `resultsSection.adverseEventsModule.eventGroups[8].seriousNumAffected`
4. **Common AE Sample**:
   - `Row ID`: `a-rebuild-safety-row_00080859210571324a8bef93` (`NCT03131648`, `tralokinumab`)
   - `Term / Category`: `Headache` / `常见不良事件`
   - `Arm / Arm Detail`: `对照组` / `Initial Period - Placebo`
   - `Numerator / Denominator / Rate`: `10` / `196` $\rightarrow$ `5.1%`
   - `Locator`: `resultsSection.adverseEventsModule.otherEvents[11].stats[1]`
5. **Zero-Denominator Sample (`numAtRisk == 0`)**:
   - `NCT03334396` (`baricitinib`), `OE14` (`Vulvovaginal candidiasis`), `Stat 6`: `groupId = 'EG006'`, `numAtRisk = 0`.
   - `NCT05131477` (`amlitelimab`), `SE10` (`Metabolic acidosis`), `Stat 3`: `groupId = 'EG003'`, `numAtRisk = 0`.
   - **Audit finding**: Denominator 0 is recognized as uncomputable. No rate is fabricated as `0%`. Documented cleanly as manifest issue `kind: not_reported`.
6. **Explicit "NA" Not-Reported Sample**:
   - `NCT02118792` (`crisaborole`), `OM7` (*Time to Achieve Treatment Success Based on ISGA*): Source value is `"NA"` (median time not estimable since <50% achieved success).
   - **Audit finding**: Value is excluded from numerical calculation and recorded as `kind: not_reported`. 0 rows fabricated.

---

## Evidence And Assumptions

### Evidence
1. **Pytest Integration Suite**:
   - Ran `pytest tests/integration/test_atopic_dermatitis_package_rebuild.py tests/integration/test_ctgov_result_coverage_audit.py -v`.
   - Result: `6 passed in 2.67s` (100% pass rate).
2. **Pydantic Content Validation & Audit**:
   - Validated `FreshAResearchContent.model_validate` against rebuilt `.artifacts/a-atopic-dermatitis-rebuild/research-content.json`.
   - Ran `audit_clinicaltrials_result_coverage(fresh_content.report_data, fresh_content.sources, facts=fresh_content.facts)`.
   - Result: `audit.passed == True`, `issues == ()` (0 coverage issues across 6,745 outcomes, 34 TEAE, 3,956 SAE, 0 AESI, 6,105 Common AEs, 0 parse failures).
3. **Exhaustive Numeric Integrity Checks**:
   - Scanned all 10,173 safety rows and 6,755 efficacy rows.
   - Safety values > 100.0%: `0`
   - Safety rows with denominator == 0: `0`
   - Safety rows with numerator > denominator: `0`
   - Safety rows with rate calculation mismatch: `0`
4. **Fact Locator Navigation**:
   - Tested JSON path navigation for all 16,840 rebuilt facts against their corresponding raw source JSON payload.
   - Failed locators: `0` (100% addressable).
5. **Claim Fact Referential Integrity**:
   - Verified that all 45 claims reference existing facts within `fresh_content.facts`.
   - Missing claim facts: `0`.

### Assumptions Challenged & Clarified
- **Assumption 1: `otherNumAffected` can be used as a fallback for `任何TEAE` when TEAE aggregate is not explicitly reported.**
  - *Refutation & Finding*: In ClinicalTrials.gov, `otherEvents` only records events that meet or exceed a protocol-defined incidence threshold (often 5.0%), whereas TEAE requires all adverse events occurring during treatment. Aliasing `otherNumAffected` to TEAE under-reports true TEAE incidence. The rebuild pipeline correctly refuses this alias and maintains `disclosure_state = '未公开'` for unrecorded TEAEs.
- **Assumption 2: Missing measurement values (e.g. "NA", "NR", or `numAtRisk == 0`) can be converted to 0.0 or treated as parser failures.**
  - *Refutation & Finding*: Converting "NA" or zero-at-risk events to 0.0 falsely implies zero incidence. Treating them as parser errors would falsely trigger audit failures. The rebuild pipeline correctly isolates these 10 instances into `manifest["issues"]` with `kind = 'not_reported'`.
- **Assumption 3: Arm classification into binary `治疗组`/`对照组` destroys complex dosage, crossover, and period distinctions.**
  - *Refutation & Finding*: While `arm` is normalized to `治疗组` / `对照组` for portal macro-filtering and gating, `arm_detail` completely retains the full original regimen name (e.g. `Placebo Re-randomized From the 62.5 mg Arm (Part 2)`). Zero rebuilt rows have empty `arm_detail`.

---

## Risks, Gaps, And Verification Needs

### High-Impact Observations & Risks for Codex
1. **Downstream Heatmap / Table Multi-Arm Rendering Risk**:
   - In trials with multiple dosage cohorts or sequential periods (e.g. `upadacitinib NCT03569293` with 15mg vs 30mg across adults and adolescents; `amlitelimab NCT05131477` Part 1 vs Part 2), multiple safety rows exist under the same `arm` (`治疗组`).
   - *Risk*: If downstream portal renderers or aggregators key on `(trial_id, product_id, arm, term)` without including `arm_detail` or `row_id`, they might overwrite sibling dosage cohorts or display only the first arm.
   - *Remediation*: Ensure the portal table/heatmap renderer facets or distinguishes multiple arms using `arm_detail` and unique `row_id`.
2. **Handling of 72 Baseline Unreported Safety Placeholders**:
   - The candidate contains 72 safety rows with `disclosure_state == '未公开'` and `value == None` (from the baseline package for products/trials where specific TEAE/AESI aggregates were never published in CTGov or label).
   - *Verification*: Confirm that portal templates render these as explicit "未公开" / "—" badges, rather than attempting to compute a 0% rate or hiding the cell unexpectedly.
3. **Efficacy Population Labeling in Aggregated Views**:
   - Efficacy rows accurately retain `population` text (e.g. `FAS1`, `FAS2`, `Per-protocol`, `Multiple imputation`).
   - *Recommendation*: When presenting comparative efficacy tables, the UI should make `population` and `timepoint` readily visible to prevent cross-trial confounding between full analysis sets and subgroup cohorts.

---

## Recommended Next Step

1. **Final Scientific Review Synthesis**:
   - Codex can confidently proceed with synthesizing the scientific review verdict as **ACCEPTED**.
   - No data alterations, formula adjustments, or code patches are required for `research-content.json` or `rebuild_atopic_dermatitis_package.py`.
2. **Proceed to Final Handoff Package Generation**:
   - Attach the approved `ScientificReview` metadata to create the production `research-package.json` from the verified `research-content.json`.
3. **Downstream Portal & Visual Validation (Codex-led)**:
   - Codex should proceed with visual / portal rendering verification (specifically verifying horizontal scroll and multi-arm rendering in the safety heatmap component for task 5.5).
