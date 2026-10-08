# Conference Output: ci-1007-c0-real-source-review-v1 - evidence_single_object

## Output

**Proposed verdict: `veto`; disposition: `recoverable`.**

All 258 candidate observations and corresponding claims, all four source bindings, and all 60 endpoint instances were inspected. English source literals and their provenance are supported. **Six candidate Chinese descriptions materially change endpoint or safety-definition meaning.** Those errors veto the bound candidate slice; unrelated disclosures about missing Protocol/SAP do not excuse them.

Sole output written:

`runs/conference/ci-1007-c0-real-source-review-v1/source-proposed-verdict-v1.json`

The saved JSON passed the existing `validate_scientific_qc_verdict_payload`: packaged JSON Schema, Pydantic model, and cross-reference semantic validation.

This is an independent **proposal**, not a product-issuer receipt, source-adoption decision, report acceptance, or release acceptance. No source state, gate, report, snapshot, or current pointer was changed.

### Proposal identity and bindings

| Field | Value |
|---|---|
| Reviewer | `ci-1007-c0-omp-independent-v1` |
| Verdict ID | `scientific-qc-verdict_ci-1007-c0-omp-independent-v1-proposal` |
| Criteria version | `2.0` |
| Report | `C` / `v0-r24-source-review-candidate` |
| Candidate snapshot | `evidence-snapshot_30aeabd46916fdb3cdb69581` |
| Candidate content digest | `ea2cda0c98b2e01ebc1a4fc050972244126198091c6bbe69d088f582aac95b50` |
| Gate result | `gate-result_e2114353a94841ff8d08d575` |
| Coverage set | `coverage-set_55b5ade4415793bb89ba0526` |
| Review input digest | `4a2f55ca42118b26eb810ee5f930e6d80cfe1d807a38559b4eefffec49933bd5` |
| Reviewed at | `2026-10-08T18:03:23.764530+00:00` |
| Valid until | `2026-10-09T18:03:23.764530+00:00` |
| Proposal file SHA-256 | `344e42b32c2f525585aa3d8da90df2688e52e867e12bd9b6e90f38a548108e4d` |
| Computed verdict digest | `19c0d004e64c7447a353f3b1f0b9df34c2c7fc7f0680ccfec599dd590a8ffbd8` |

The proposal copies the current context’s exact bindings, four `source_refs`, and 250 locators. Its input digest is the **request’s gate-bound review input digest**, not the older bundle digest.

Runtime identity observed in authoritative session metadata: **`openai-codex/gpt-6.1-sol:high`**, matching the approved Pi route. No model change or fallback was invoked. A real session identifier was unavailable in the inspected session environment; none was fabricated. Server-side effort attestation was not available. The route manifest itself remains pre-dispatch evidence, not runtime attestation.

### Inspected coverage and provenance

Let **P** denote `.artifacts/1007-c-source-review-bootstrap-worker-v1/project`.

| Registry study | Source version | Observations/claims | Endpoint instances |
|---|---|---:|---:|
| NCT04183335 | `source-version_c3fc5ac6e6f0a02c8744c4c7` | 86 | 21 |
| NCT04202679 | `source-version_a6c43a83dd64957ec923e735` | 92 | 23 |
| NCT04501666 | `source-version_c17a4653ec8903dc9c822c60` | 40 | 8 |
| NCT04501679 | `source-version_0f3c63f7f5acf2cd2aa83a7b` | 40 | 8 |

Coverage included population/eligibility, trial identity, allocation/model/masking, experimental and control interventions, dosing, enrollment, endpoint measures, descriptions, and time frames.

Observed checks—not counts alone:

- Reopened the captured raw CAS at  
  `P/evidence/raw/sha256/82/82b4ed9ab0c63e227a2c4c34b85727dd988e55062850d42b41517f0749168edf.bin`.  
  Its 2,978,130 bytes matched the declared SHA-256.
- Selected raw study indices **24, 10, 31, 46**. Each selected NCT identity and complete study object matched its saved source slice. Serialized slice text and declared text hashes matched.
- Resolved every observation locator against its corresponding study object: **250 exact field literals and eight supported eligibility substrings**. The eight inclusion/exclusion facts retain the complete eligibility field as their original/raw quote and the supported section as their normalized value; this is not a quote mismatch.
- Checked all 258 fact scientific-context hashes, v3 fact identities, primary-fragment/source associations, claim identities, and claim-to-fact genealogy against the snapshot and an **immutable, read-only SQLite connection**.
- Checked all 254 snapshot fragment rows against the database. The context’s 250 locators matched the referenced snapshot locators.
- Recomputed all four source-version identities, the production-context digest, request digest, and gate-bound review input digest successfully.
- The saved library `report-data.json` contains the same 258 observation payloads as the pending input, including the erroneous Chinese descriptions.
- Trial/product, arm, endpoint-instance and time-frame associations showed no discrepancy. In particular, **PRIME2 arm 0 is placebo and arm 1 is dupilumab**; its candidate bindings respect those labels rather than assuming experimental-arm ordering.

All inspected fact, claim, and observation review states remained `candidate`.

### Blocking source disagreements and smallest repairs

All paths below are within the corresponding captured study JSON. English literals are correct; the disagreement is in candidate `display_text`.

#### 1. IGA PN-A activity is mistranslated as lesion clearance/cure

Affected observations:

- `obs-nct04183335-sec16-description`  
  Path: `$.protocolSection.outcomesModule.secondaryOutcomes[16].description`  
  Fact: `fact-version_45fa2ac65c12259cc0dee9bc`  
  Fragment: `evidence-fragment_345d94773e4036ebc48f5ec6`
- `obs-nct04202679-sec18-description`  
  Path: `$.protocolSection.outcomesModule.secondaryOutcomes[18].description`  
  Fact: `fact-version_33edb07a80e4df7ac929ad52`  
  Fragment: `evidence-fragment_1ab56f5c9e208f374efb4b66`

**Observed:** The source defines IGA PN-A activity score 0 as **0% of nodules showing excoriations/crusts**, and score 1 as **up to 10%**. Both Chinese descriptions call these states “皮损完全消退” and “几乎痊愈”, then repeat those interpretations in the response summary.

**Scientific interpretation:** Absence or near-absence of excoriation/crusting does not establish disappearance of nodules or cure. Correct percentages in parentheses do not neutralize contradictory prose.

**Smallest repair:** Translate clearance of **activity signs**, not disappearance of lesions or cure. Preserve the complete 0%, ≤10%, 11–25%, 26–75%, and 76–100% definitions. Do not alter the English literal, endpoint identity, or time frame.

#### 2. SAE disability/incapacity criteria are narrowed

| Observation | Exact source path | Fact version | Fragment |
|---|---|---|---|
| `obs-nct04183335-sec18-description` | `$.protocolSection.outcomesModule.secondaryOutcomes[18].description` | `fact-version_ef261ca2371b52cf81799756` | `evidence-fragment_8ba02ea6033213b8fa3be5ab` |
| `obs-nct04202679-sec20-description` | `$.protocolSection.outcomesModule.secondaryOutcomes[20].description` | `fact-version_de727fae0ad97d8b46ba132d` | `evidence-fragment_b0e87d091b2db797d2820a2d` |
| `obs-nct04501666-sec0-description` | `$.protocolSection.outcomesModule.secondaryOutcomes[0].description` | `fact-version_6391f2922bd2fc0146a3addf` | `evidence-fragment_c61409e823599da341c480b6` |
| `obs-nct04501679-sec5-description` | `$.protocolSection.outcomesModule.secondaryOutcomes[5].description` | `fact-version_955d79158edb6af4db5af114` | `evidence-fragment_f334d4f81792a4f540e3a14b` |

**Observed:** All four sources say **“persistent or significant disability/incapacity.”**

- Dupilumab descriptions use “永久性或显著的残疾/丧失行为能力”.
- Nemolizumab descriptions use “永久性显著残疾/丧失能力”, additionally omitting the explicit **or**.

**Scientific interpretation:** Persistent is not necessarily permanent. The nemolizumab wording also collapses alternative criteria into an apparently combined requirement. “丧失行为能力” is narrower than general incapacity.

**Smallest repair:** Use “持续性或显著的残疾/功能丧失”, retaining the alternatives and other independent SAE criteria.

The same two nemolizumab paragraphs define AESI using “与研究药物相关” as a qualification. The English describes a noteworthy TEAE requiring close monitoring and prompt reporting, then separately assigns relatedness assessment to the investigator. Remove the added causal qualification; do not equate special-interest designation with established drug causation.

The six affected direct claims are respectively `claim-` plus each observation’s `c-…-description` row ID. Their exact source-version and fragment bindings are retained in the proposal’s six blocking issues.

These repairs are bounded translation corrections. No new architecture or source-content fabrication is needed. This frozen proposal must remain unchanged; any repaired candidate requires its own updated identity and review.

### Dates, enrollment, unknown relationships, and registry limitations

**Posted version versus first study disclosure**

| Study | Current version posted day | Registry study-first-posted day |
|---|---|---|
| NCT04183335 | 2025-09-17 | 2019-12-03 |
| NCT04202679 | 2025-09-17 | 2019-12-17 |
| NCT04501666 | 2024-07-10 | 2020-08-06 |
| NCT04501679 | 2024-07-10 | 2020-08-06 |

The captured dates resolve to `$.protocolSection.statusModule.lastUpdatePostDateStruct.date`. I checked the current contract rather than inferring semantics from producer status: `source_capture_from_ctgov_study`, lines 343–347, explicitly defines this as disclosure of the **current record version**. The pending metadata separately says it is not the study’s first disclosure.

Therefore, the difference above is **not independently a date veto under this version-scoped contract**. These dates must not be presented as first-ever study disclosure or used to reconstruct an earlier historical record. Replacing them with study-first-posted dates would incorrectly backdate the current record version.

**Actual versus planned N**

The registry enrollment counts are **ACTUAL: 151, 160, 286, 274**. Candidate Chinese displays identify them as actual enrollment. Planned and treatment sample sizes remain null. These are not demonstrated planned targets, arm denominators, or analysis-population counts.

**Unknown associations**

Thirty-six arm observations have explicit label-supported bindings. Study-level observations retain study-wide context; endpoint records do not invent result-arm or analysis-set associations. `period` and `development_role` remain unset. Empty product links and unverified developer, mechanism, regulatory and product-stage fields remain limitations—not inferred closures.

**Endpoint distinctions preserved**

- PRIME’s primary WI-NRS response is at week 24; PRIME2’s is at week 12.
- Nemolizumab records retain two primary endpoint instances at week 16.
- Descriptions, measures, and time frames remain separate.
- ANCOVA LS means/SE and Kaplan–Meier probabilities are not replaced with crude percentages.
- Rescue/missing-data wording differs between the nemolizumab studies and remains source-specific.
- NCT04501666’s safety time frame says **24 weeks**, while its dosing descriptions say **16 weeks**. Both are present in the raw capture; this replay does not justify silently reconciling them.

**Truncated source tail**

`obs-nct04501666-sec4-description`, at  
`$.protocolSection.outcomesModule.secondaryOutcomes[4].description`, genuinely ends in **“non-responde”** in the raw CAS. The Chinese display flags the truncation and does not complete the missing clause. This is an observed upstream limitation, not a local extraction cap and not permission to infer the tail.

### Full-report boundary and unaccepted limitations

The actual request contains **64 unit results**:

- **28 blocked** core results: seven families across four trials;
- **32 `extension_missing`** results: eight statistical families across four trials;
- **4 `not_applicable`** results.

The context’s “28” describes blocked core results, not the total result count. Candidate-only facts explain the pre-adoption core blockage; that does not mean the underlying supported registry fields are absent.

Full-report gaps remain in:

`c_analysis_population`, `c_comparison_logic`, `c_effect_size`, `c_estimand_intercurrent`, `c_missing_data_sensitivity`, `c_multiplicity`, `c_sample_size_assumptions`, and `c_statistical_model`.

Protocol/SAP bodies were not reviewed or ingested in this pass. Registry descriptions mentioning analysis methods or SAP do not close those documents or statistical requirements. The four studies are a fixed representative PN slice, not a demonstrated complete indication/product/publication universe. No cross-trial equivalence, head-to-head conclusion, dynamic-status freshness, or historical reconstruction was accepted.

### Input hashes and verification status

SHA-256 hashes of bytes actually reopened:

| Input under P | SHA-256 |
|---|---|
| `inputs/c-source-review/pending-content.json` | `15c86dd170de46718b47e061b922f2ca67fabacc2c86003786b819da862dc5d4` |
| `state/scientific_review/C/review_request.json` | `7d2326062faba91464e3eea8656a65828d0bcad58f2df017e4d6f43f109b9b90` |
| `state/scientific_review/C/production_context.json` | `120ec574c9261b2596090dbb158204754fb3658833f24a962ad9cdabd08f902f` |
| Candidate evidence snapshot JSON | `7d53d370751279ffdc175f03e639b3d50e124ac5948b10c86c1831644b8856f2` |
| Candidate library `entry-receipt.json` | `d91881f77771c65800f096877e3a95a4a02050853dcb945970d676f024ff0f60` |
| Candidate library `report-data.json` | `80aeb75f4e6255f26882e4a0814ca2aec645a32fcecfac0c381b313a24d57f05` |

The request’s verified internal `request_digest` is `b0d3991f51b59c78458674faf281fb436b286210ee8e746d8ccdb3b416402ff7`; the verified internal context digest is `2d3bfb6df3b298aeb69a1ca849c8eb73d8e1efbe8805053c14902428a55c2967`. These are distinct from file-byte hashes.

Verified study-text hashes:

- NCT04183335: `23935d3e46b135b0a0f22372883b38fd16c10df390f2a5fc639f3b10bb291081`
- NCT04202679: `db8af66ab1287a5b3c1c41beb456638167fdbad46b919f4299251416dde6124a`
- NCT04501666: `d9d88f9e2663941344df0bacca99e06237506919b9e9109da607fab92ae30f7f`
- NCT04501679: `077b433a4bab52a04c36279db3992bf3c1cd4cd10c56c0bddc1d81316790d8ef`

**NOT_RUN:** browser/visual acceptance, live fetching, Protocol/SAP-body review, pytest, project execution, `smoke_real258.py`, product issuance, source adoption, gate reevaluation, current switching, and release checks. No recursive dispatch, cleanup, or additional output-file write occurred.
