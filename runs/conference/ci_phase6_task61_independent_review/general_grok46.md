I'll start from the assigned conference context and plan, then independently audit Task 6.1 against the actual contract and evidence rather than test summaries.The conference packet is a stub, so I’ll locate the Task 6.1 contract, implementation, and tests in the workspace and audit those as the source of truth.I’ll pull the Task 6.1 contract, implementation, policies, and tests next, then challenge them against original semantics rather than pass/fail counts.Implementation is in place; next I’ll read the study-role policy, YAML rules, and tests to look for incorrect inclusion and semantic drift.I'll run adversarial probes next: non-NCT publication tampering, construct injection, and study-role fall-through, because those are the most likely false-green paths.19 tests passed; that is not acceptance. The probes show wrong-inclusion and identity-bypass holes that the tests never touch. The report below is the independent review for Codex.

# Conference Participant Output: ci_phase6_task61_independent_review - general_grok46

## Boundary Check

- Role: `general_grok46` / Grok Build `grok-4.6`. Conference mode: parallel. No other participant files were read.
- Workspace only. No production paths, no source edits, no report-file writes, no internet scan, no visual/PPT/browser acceptance.
- Initial read: `context/ci_phase6_task61_independent_review_conference_context.md`, `plans/codex_main_venue_ci_phase6_task61_independent_review.md`. Both are TODO stubs; they are **not** a source of truth.
- Additional reads (because the packet is empty): execution context/plan; `docs/specs/competitive-intelligence-workflow-design-v1.2.md` §3.2 / §9 / §13.1–13.3 / §14.1; `src/ci_workflow/reports/common/study_roles.py`; `src/ci_workflow/reports/b/contracts.py`; `src/ci_workflow/sources/connectors/pubmed.py`; policies `policies/studies/study-role-v1.yaml`, `policies/endpoints/compatibility-v1.yaml`, `policies/timepoints/compatibility-v1.yaml`; the three designated tests; `policies/gates/B-v1.yaml` (identity/role unit only).
- Tools used: workspace grep/read; `uv run python` adversarial probes; `uv run pytest` on the three designated files. Observation: `19 passed in 0.25s`.
- This pass does **not** claim final clinical, regulatory, or product acceptance.

## Independent Work Product

### Objective audit (before conclusions)

Task 6.1 is a fail-closed **contract** layer, not a page layer. The product contract requires:

1. `study_role` and `publication_role` stored separately; a post-hoc paper must not rewrite the mother trial.
2. Default-exclude five classes (healthy volunteer, pure PK/BE, unrelated indication, general observational, EAP/compassionate use); rescue to supporting only with a **named** safety/regulatory/special-population problem and irreplaceable evidence.
3. Early special-core only for rare disease / oncology / accelerated development with auditable decision evidence.
4. C early studies enter design analysis only with a concrete dose/endpoint/adaptive/population/estimand/registration-logic dependency.
5. Fuzzy endpoint/time-window families form **only** on versioned rules; every record keeps original endpoint, unit, actual timepoint, analysis form, rule IDs, **and difference labels**.

The execution work item and the three tests encode a **narrower** subset: five exclusions, named-problem supporting rescue, special-core, C decision domain, B two-column output, YAML load fail-closed, and a few compatibility mismatches. Independent review must not treat that subset as the v1.2 contract.

### Highest-impact defects (do not accept on green tests)

**P0-1. Non-NCT `study_id` skips publication reclassification; `model_copy` can plant a fake `publication_role`.**

Evidence: `_validated_publication` in `src/ci_workflow/reports/b/contracts.py` re-runs `classify_pubmed_records` only when `study_id` full-matches `NCT[0-9]{8}`. Otherwise it `model_validate`s the already-classified object. `ClassifiedPublication` has no validator that re-derives `role` from `record`.

Probe: `study_id=ChiCTR2100000001` + `publication.model_copy(update={"role": "review", ...})` → **ACCEPTED**, output `publication_role=review`, while `study_role` stayed `core`. NCT-path role tamper is rejected (test covers that path only).

This is a China-trial hole in a CDE-facing product. Tests never use a non-NCT identifier.

Remediation: always reclassify from `publication.record` (or refuse the publication). Do not key the integrity gate on NCT regex. If China/EU identifiers have no PubMed NCT classifier, fail closed with `unclassified` / error, do not trust caller `role`.

**P0-2. Caller-supplied `clinical_construct` can force a foreign endpoint into a fuzzy family.**

Evidence: `_endpoint_match` uses `candidates = by_endpoint_id or by_construct`. Unknown `endpoint_id` falls through to construct match.

Probe: `endpoint_id=pasi75` (PASI-75) + `clinical_construct=easi75_response` + `%` + `response_rate` + week 12 → **`compatible=True`**, `endpoint_rule_id=endpoint-easi75-response-v1`, empty difference labels.

Asymmetry: `easi75` + `clinical_construct=nasal_polyp_score` correctly fails (`临床构念不兼容`). Construct is therefore a **bypass key**, not only a consistency check.

This is incorrect inclusion into a fuzzy-match bucket. Spec §13.3: families form only when versioned rules hit; the model must not merge on the spot. Here the “model” is any upstream writer of `clinical_construct`.

Remediation: `clinical_construct` may only confirm a rule already hit by `endpoint_id` (and direction/unit/form). If `endpoint_id` is not in `endpoint_ids`, split. Do not `or by_construct`.

**P0-3. B supporting layer cannot represent §13.1’s second population; ordinary early / RWE / extension / subgroup fall through to unnamed exclusion.**

Evidence:

- Spec §13.1: 早期、延伸、亚组、事后、真实世界等进入支持层并明确角色.
- Spec §3.2 supporting rescue is only for the five default-exclude classes.
- `StudyCandidate` fields are only: phase, design_category, indication_relation, booleans, named_issue, decision_domain. No extension / OLE / subgroup / post-hoc / RWE / evidence-layer type.
- Probe: ordinary B Phase I interventional, target indication, with results → `excluded`, `matched_rule_ids=()`, rationale `未命中适格研究角色规则，证据不足时默认排除。`
- Probe: observational (RWE) without named-issue rescue → excluded by `exclude_observational`; with a free-text named_issue + `evidence_is_irreplaceable=True` → supporting even if the “issue” is `随便写的问题标题`.

Tests lock in §3.2 rescue-only supporting and never ask for §13.1 supporting classes. That is a **false-green contract**, not proof of spec completeness.

This is the main **wrong-exclusion** risk: early/OLE/RWE evidence disappears from B instead of sitting in a labeled supporting layer. It is also a **wrong-inclusion** risk on the rescue path: three caller booleans/strings (`named_issue`, `issue_domain`, `evidence_is_irreplaceable`) mint supporting without locator or irreplaceability proof.

Remediation (needs Codex ruling, see questions): either (i) extend the candidate/policy so target-indication early/extension/RWE/subgroup derive `supporting` with an explicit role tag, and require evidence locators for rescue, or (ii) explicitly defer §13.1 supporting classes to a later task and record the spec contradiction. Silent “tests passed” is not (ii).

### Additional material defects

**P1-1. Compatible records are forbidden from carrying difference labels; within-window originals are erased as semantics.**

`EndpointCompatibilityResult._result_consistency` raises if `compatible and difference_labels_zh`. Probe: `timepoint=10`, `time_unit=week` → compatible, `timepoint-week-12-v1`, **labels `()`**. Spec §13.3 requires every record to keep original timepoint **and** 差异标签. Week 10 is not week 12; the bucket hid the difference.

YAML `difference_label_zh` is only used as a Chinese-character presence check at load time. Matcher emits hardcoded labels (`方向不兼容`, `单位不可直接换算`, …) and never the rule text.

Remediation: compatible hits must still emit a deterministic within-bucket difference tag (actual vs canonical window/unit/endpoint alias). Remove the “compatible ⇒ no labels” invariant. Drive mismatch labels from the rule, or keep both rule labels and mechanical reasons.

**P1-2. `TrialRoleOutput` is not a self-authenticating object.**

`build_trial_role_output` recomputes `study_role` and (for NCT) publication role. The output model itself has no invariant: direct construct and `model_copy(update={"study_role": excluded, "publication_role": "review"})` both succeed. A-class lineage objects re-validate against source; this B contract does not. Any later consumer that accepts a frozen `TrialRoleOutput` can be fed a swapped pair.

Remediation: store the candidate + publication record (or their content digest) on the output and re-derive both roles in a model validator, or refuse `model_construct` / require factory-only build with a sealed hash.

**P1-3. Study-role policy has no overlap/ambiguity gate; YAML order plus priority is the hidden adjudicator.**

Endpoint/timepoint policies reject overlapping rules. Study-role policy only rejects duplicate IDs/bodies. Probe: cloned `core_b` with `priority=81` loads; evaluation winner is the clone, `matched_rule_ids` contains both. Two equal-priority matches sort by YAML index.

This is rule ambiguity. Supporting (60) beating exclude (10) is intended; two different core rules is not.

**P1-4. `is_key_or_registration` / `has_results` / `evidence_is_irreplaceable` are unstructured caller assertions.**

Phase III target interventional with results but `is_key_or_registration=False` → unmatched exclude. Marking the same study pivotal includes it as core. There is no registry/label/phase-3-pivotal evidence binding. Wrong inclusion of exploratory Phase II as core is a one-boolean change. This layer cannot see that lie.

**P1-5. C “specific rationale” gate is a denylist, not a reason.**

Probe: C Phase I + `decision_domain=dose` + rationale `重要证据` → **core** (`c_early_decision_domain`). Tests only block `这项研究很重要。`. Spec §14.1 wants a concrete dependency on dose/endpoint/…. `重要证据` is not that.

**P1-6. Time-unit conversion is absent; labels mis-describe the miss.**

Comment in code: 初版不做单位换算. Probe: EASI-75 at **84 days** (≈12 weeks) → incompatible, `时间点超出兼容范围`, because a **day-28** rule exists (26–30) and 84 is outside it. Probe: **3 months** vs week-12 → same label, because month-6 window is 5.5–6.5. These are not “out of the 12-week window”; they never entered a convertible family. Spec talks about 可换算单位 for endpoints; time windows are per-unit closed intervals. First-version no conversion can be a documented limit, but the label is scientifically misleading and will look like a 12-week observation was compared to day 28.

**P1-7. `can_replace_primary_report` is not in the NCT revalidate tuple.**

NCT role tamper is caught; `can_replace_primary_report` tamper is accepted. Field is not copied onto `TrialRoleOutput`, so current factory impact is limited. It remains a lineage hole if anyone later reads the validated `ClassifiedPublication`.

**P1-8. Tests are not an adversarial contract.**

`19 passed` covers: five mechanical excludes; supporting rescue with irreplaceable flag; special-core flag; C generic `很重要`; two-column output; post-hoc paper does not change mother role; NCT publication `model_copy` role; extra `study_role` on candidate dict; raw definition/unit preserved on one happy path; direction/unit/form mismatch split; timepoint 20 split; unknown YAML field / duplicate body / non-Chinese label / overlapping endpoint & window rules; observation unit `model_copy` rematch.

They do **not** cover: ChiCTR; construct-only match; week 10 vs 12 labels; ordinary early B; RWE as supporting; output `model_copy`; overlapping study-role rules; weak C rationale; unit conversion; `can_replace` tamper; adjacent indication; non-pivotal Phase III.

### What is actually working (observation, not acceptance)

- Candidate `extra=forbid` rejects injected `study_role`.
- Factory path keeps mother `study_role` stable across primary vs post-hoc papers **when both go through `build_trial_role_output` with the same candidate**.
- NCT-path publication role is re-derived from title/abstract/types + target NCT.
- Five default-exclude design classes match named exclude rules; named-problem + irreplaceable can promote them to supporting (priority 60 > 10).
- Special-core requires rare/oncology/accelerated + irreplaceable + decision domain + non-generic rationale.
- C early ordinary with a listed decision domain can become C core; missing domain or `这项研究很重要` is excluded.
- Endpoint/timepoint YAML unknown fields, duplicate bodies, overlapping families/windows, and missing CJK difference labels fail closed.
- Compatible path preserves raw `endpoint_definition` / `unit` / actual timepoint string (including `第12周`) without overwriting originals.
- Direction/unit/analysis mismatch splits and still records a timepoint rule when the window hits.
- A-class `analysis.py` does not import `evaluate_study_role` (no immediate A semantic rewrite observed from this import graph).

### Draft / output plan (advisory)

Do not write code in this round. Suggested repair order if Codex opens an edit round:

1. Close P0-1: reclassify every publication from `record`; non-NCT → fail closed or `unclassified`, never honor caller `role`.
2. Close P0-2: construct is confirmation only; unknown endpoint_id never joins a family.
3. Codex ruling on P0-3 / §13.1 vs §3.2; then either extend schema/policy or record an explicit deferral in the task verdict.
4. Allow/require within-bucket 差异标签; stop using “no labels” as the compatible invariant.
5. Seal `TrialRoleOutput` (re-derive or hash).
6. Add study-role overlap checks analogous to endpoint/timepoint.
7. Replace boolean-only irreplaceability / pivotal flags with evidence-bound facts, or mark them as temporary upstream trust with a fail-closed TODO in policy metadata.
8. Expand tests to the probes above; keep the current 19 as regression, not as the ceiling.

## Evidence And Assumptions

### Evidence

- Conference context/plan: Source of Truth / Scope / Success Criteria / Codex checklist are TODO.
- Product spec v1.2 §3.2, §13.1, §13.3, §14.1 as quoted above (file read).
- Implementation: `study_roles.py`, `reports/b/contracts.py`, `pubmed.py` `_classify` / `classify_pubmed_records`, three YAML policies (file read).
- Tests: 19 passed (`tests/reports/test_study_role_policy.py`, `tests/reports/b/test_trial_roles.py`, `tests/reports/b/test_endpoint_compatibility.py`).
- Live probes (this session, `uv run python`): ChiCTR forged publication accepted; PASI-75+`easi75_response` compatible; ordinary B Phase I unmatched-excluded; non-pivotal Phase III unmatched-excluded; adjacent pivotal Phase III unmatched-excluded; `重要证据` C core; observational+junk named_issue supporting; week 10 compatible with empty labels; 84 day / 3 month mislabeled as 超出范围; cloned overlapping core rule loaded; `TrialRoleOutput.model_copy` swapped roles; NCT role tamper rejected; candidate extra `study_role` rejected.

### Assumptions

- Task 6.1 is in-repo contract only; pages and live B/C reports are out of this task (execution context: 不创建页面).
- Structured `StudyCandidate` fields are **not** yet bound to atomic facts/locators in this layer.
- PubMed classifier remains NCT-centric; that is inherited, not introduced here, but B wiring must not treat it as universal.
- No conversion of week↔day↔month is an intentional v1 limit unless Codex says otherwise.

### Inference

- Green tests are a **subset encoding** of the execution prompt, not of v1.2. Several P0 paths are untested by construction.
- Highest practical harm: (1) China trial papers with planted roles; (2) construct-key merging of incommensurable endpoints into one efficacy bucket; (3) early/RWE/OLE studies vanishing from B or being smuggled in via unchecked booleans.

### Uncertainty

- Whether Codex intends Task 6.1 supporting layer to be **only** five-class rescue (execution item) or also §13.1 early/extension/subgroup/RWE. This changes P0-3 from “missing contract” to “explicit deferral”.
- Whether `clinical_construct` was meant as an ontology ID filled only by a later deterministic mapper. Even then, using it as an `or` match key is unsafe.
- Whether later 6.x tasks will seal `TrialRoleOutput` at snapshot lock. Currently nothing does.
- Visual/page consequences of empty compatible difference labels were not rendered (out of role).

## Risks, Gaps, And Verification Needs

| ID | Type | Risk | Verification still needed |
|---|---|---|---|
| P0-1 | Wrong publication role / lineage | Non-NCT `model_copy` plants review/primary | Tests with ChiCTR/EudraCT/CDE ids; factory must reject or reclassify |
| P0-2 | Wrong inclusion into fuzzy family | PASI-75 labeled as EASI-75 family | Construct-only match must be incompatible; endpoint_id required |
| P0-3 | Wrong exclusion / spec split | Early/OLE/RWE absent from B supporting | Codex ruling; then schema+policy+tests or written deferral |
| P1-1 | Original semantics lost | Week 10 ≡ week 12 with no 差异标签 | Compatible result must still show actual vs canonical |
| P1-2 | Output tamper | Frozen output roles swapped | A-style revalidation or sealed factory |
| P1-3 | Rule ambiguity | Overlapping study-role rules | Loader must reject overlapping eligibility, not only duplicate bodies |
| P1-4 | Boolean authority | Pivotal/irreplaceable flags mint core/support | Bind to facts/locators or mark untrusted |
| P1-5 | Weak C gate | `重要证据` → C core | Rationale must name the decision domain dependency |
| P1-6 | Misleading split reason | 84d labeled 超出范围 vs day-28 | Conversion policy or unit-mismatch label |
| Tests | False green | 19 passed | Adversarial cases above must exist before acceptance |

Do not treat worker “RED then GREEN” logs as independent verification. This review did not open `runs/conference/.../general_pi_antigravity.md`.

## Recommended Next Step

**Codex should not accept Task 6.1.** Treat current tests as necessary regression only.

Immediate chair actions:

1. Record P0-1 and P0-2 as blocking contract defects (publication identity; construct-only matching).
2. Answer the bounded questions below; P0-3 cannot be closed honestly without that ruling.
3. If an edit round is opened, require adversarial tests that replay the probes in this report, not another happy-path expansion.
4. Safe provisional path until then: keep fail-closed unmatched studies **out of core**; do **not** ship construct-or matching; do **not** trust `publication_role` unless `study_id` was reclassified from `record`; do not tell users the compatibility layer preserves 差异标签 on compatible rows.

### Objections

- Objection to “19 passed ⇒ contract complete”: the designated tests never instantiate the China-trial, construct-injection, within-window label, or §13.1 supporting-class cases.
- Objection to treating `_validated_publication` NCT regex as sufficient `model_copy` defense: it is identifier-shaped, not content-shaped.
- Objection to `compatible ⇒ difference_labels must be empty`: it directly contradicts §13.3’s “每条记录保留…差异标签” and hides week-10 vs week-12.
- Objection to supporting layer = named-issue rescue only: that is §3.2, not the full B §13.1 sentence, and the candidate schema cannot even name OLE/subgroup/RWE.

### Proposed solutions

- Reclassify publications from raw `PubMedRecord` for every `study_id`; non-NCT → `unclassified` or hard error.
- Match endpoints by `endpoint_id` ∩ direction ∩ unit ∩ analysis_form; use `clinical_construct` only as a consistency constraint.
- Emit within-bucket difference labels from actual vs canonical/window/alias; drop the empty-label invariant.
- Either add typed study-layer facts for early/extension/RWE/subgroup, or formally defer them in the Task 6.1 verdict.
- Seal `TrialRoleOutput`; add study-role overlap rejection; tighten C rationale to mention the bound `decision_domain`.

### Decision points / bounded questions for Codex

1. **Supporting population:** For Task 6.1, is B `supporting` only the five-class rescue path (§3.2 + current YAML), or must target-indication early / extension / subgroup / post-hoc / RWE also be `supporting` (§13.1)? This decides whether P0-3 is in-scope failure or documented deferral.
2. **Non-NCT papers:** Must `publication_role` revalidation run for ChiCTR/EudraCT/CDE identifiers in this task, or is PubMed-NCT the only in-scope identity until a China publication classifier exists? If the latter, the factory must still refuse caller-supplied roles instead of accepting them.
3. **Construct matching:** Is `clinical_construct` allowed to create a family when `endpoint_id` is not on the rule, or only to refute a family? Provisional recommendation: refute-only.
4. **Compatible 差异标签:** Must a week-10 observation that falls in the 10–14 week window carry a difference label, or is “compatible ⇒ no label” an intentional v1.2 relaxation? Spec text does not support the relaxation.
5. **Pivotal/irreplaceable booleans:** Are they accepted as already-gated upstream facts for 6.1, or must this layer demand locators? If upstream-trusted, say so in the verdict so later snapshot QC owns the lie.

Until (1)–(4) are answered, the safe path is: **not accepted**, fail closed on construct-only matches and non-reclassified publication roles, and do not describe the current YAML+tests as fulfilling the full v1.2 study-role / compatibility contract.
