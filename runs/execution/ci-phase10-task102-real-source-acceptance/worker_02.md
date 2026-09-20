# Execution Output: ci-phase10-task102-real-source-acceptance - worker_02

## Boundary And Context Check

- Scope limited to R03 source resolution and evidence artifacts.
- Writes stayed under:
  - `runs/acceptance/task-10.2-20260901-123524/inputs/a-real/**`
  - `runs/acceptance/task-10.2-20260901-123524/research/a-real/**`
- No production source or test files changed.
- No runner-managed `runs/execution/**` report written.
- No PDF, HTML-PPT, PPTX, browser, visual, Chinese-language, or final Codex acceptance performed.

## Work Performed

### Registry projection resolution

Replaced the eight previously retained current ClinicalTrials.gov records with exact official pre-cutoff history snapshots. All eight fresh history requests returned HTTP 200 and were archived with raw and canonical hashes:

- `NCT03349060` history v47
- `NCT03703102` history v10
- `NCT03809663` history v34
- `NCT03985943` history v39
- `NCT04146363` history v31
- `NCT05131477` history v23
- `NCT05608343` history v12
- `NCT05509023` history v10

Projection audit after replacement:

- Result parse failures: `0`
- Product status mismatches: `0`
- Remaining projection gaps: `0`
- Registry audit: passed

### NCT05509023

Resolved from official history v10:

- Trial: `SIGNAL-AD`
- Registry identity: `NCT05509023`
- Intervention: `ADX-914` / bempikibart
- Arms: ADX-914 and placebo
- Status: `COMPLETED`
- Phase: `PHASE2`
- Actual enrollment: `121`
- Results first submitted: `2026-01-29`
- History locator prefix:
  `https://clinicaltrials.gov/api/int/studies/NCT05509023/history/10`

Added source-bound rows:

- Efficacy: `7` rows, all numeric
  - Part B EASI week 14
  - Part B adverse-event incidence outcome
  - Part A EASI week 14
- Safety: `25` numeric rows
  - Serious AE aggregate and individual serious events
  - Other AE aggregate and individual other events
- Explicit unreported safety sentinels: `4`
  - Any TEAE, treatment/control
  - AESI, treatment/control
  - `value: null`, `disclosure_state: 未公开`
  - No zero inference

Decisive locators use exact result paths under:

- `resultsSection.outcomeMeasuresModule.outcomeMeasures[...]`
- `resultsSection.adverseEventsModule.eventGroups[...]`
- `resultsSection.adverseEventsModule.seriousEvents[...]`
- `resultsSection.adverseEventsModule.otherEvents[...]`

Product/trial identity is bound to `bempikibart` and `nct05509023`; arm labels are preserved as treatment/control.

### NCT05608343

Resolved from official history v12:

- Product: difamilast
- Trial: `NCT05608343`
- Enrollment: `153`
- History locator prefix:
  `https://clinicaltrials.gov/api/int/studies/NCT05608343/history/12`

Added source-bound rows:

- Efficacy: `4` numeric rows
  - Treatment: `94/94`, `100.0%`
  - Vehicle: `59/59`, `100.0%`
  - Two registered efficacy outcome measures
- Safety: `8` numeric rows
  - Any SAE
  - Other AE aggregate
  - Thyroid Cancer
  - Contact Dermatitis

### Nonregistry source revalidation

Freshly revalidated all `44` nonregistry sources used by the package:

- `42` exact primary-body re-fetches
- `2` scoped alternative-route revalidations:
  - Wiley → Crossref metadata/API
  - NEJM → PubMed XML identity/abstract route

Relevant limitations were recorded:

- Wiley publisher routes remained unavailable. Crossref supports DOI identity, the primary-study relationship, the EASI-75 treatment-control delta, and reported safety rates. Two unsupported arm-level direct claims were removed:
  - `curated-result-claim_07fd83f90004964eedfae9e2`
  - `curated-result-claim_b0f6963058490900c825c109`
- NEJM publisher route remained unavailable. PubMed XML revalidated PMID/DOI/trial identity. The exact Table 3 any-AE pair remains only because marketed-product completeness requires numeric treatment/control TEAE evidence; no replacement or zero inference was introduced.

### Package and audit recomputation

Current package:

- Products: `38`
- Trials: `49`
- Efficacy rows: `6791`
- Safety rows: `10265`
- Regulatory rows: `76`
- Company rows: `38`
- Patent rows: `38`
- History rows: `41`
- Sources: `88`
- Facts: `17175`
- Claims: `146`

Current digests:

- Research package SHA-256:
  `c196f67fadbafeb699dd682078a4044da4ea014b6d82ebfa8fcf0152f112bb90`
- Research content digest:
  `88bf766c56be55b739c19835f3a7b63fe27f9e0e5a0c5aa2446f2ae73257a93d`

Cutoff audit:

- Eligible sources: `88`
- First disclosed after cutoff: `0`
- Acquired after cutoff: `88`
- All eight resolved registry records use archived historical versions.
- No current registry record remains retained for the prior projection-gap reason.

Coverage summary:

- Products with public key results: `26`
- Products with partial public results: `3`
- Products without public key results: `9`
- Product/trial/domain missingness was recomputed and persisted.
- Explicit `未公开` safety values remain distinct from numeric zero.

## Artifacts And Evidence

Primary package:

- `runs/acceptance/task-10.2-20260901-123524/inputs/a-real/evidence/library/a-research-package.json`

Resolution and audit artifacts:

- `research/a-real/fresh-revalidation.json`
- `research/a-real/fresh-revalidation-evidence.json`
- `research/a-real/source-index.json`
- `research/a-real/cutoff-audit.json`
- `research/a-real/coverage-matrix.json`
- `research/a-real/research-provenance.json`
- `research/a-real/smoke-run-evidence.json`

Lineage and raw re-fetches:

- Old package:
  `research/a-real/lineage/a-research-package-before-r03-resolution.json`
- Old source contents:
  `research/a-real/lineage/source-content/**`
- Registry history raw responses:
  `research/a-real/fresh-revalidation/raw/**`
- Alternative nonregistry responses:
  `research/a-real/fresh-revalidation/alternate/**`

Updated smoke evidence:

- `research/a-real/smoke-run-evidence.json`
- Evidence SHA-256:
  `a4ff062306393d5b50cf788177d7bb9c0504456ace0b60f4ce63f3a6810ee36f`

## Commands And Observations

### Package loader and registry audit

- `load_fresh_a_research_package(...)`
  - passed
  - digest matched `88bf766c...`
  - counts matched current package
- `audit_clinicaltrials_result_coverage(...)`
  - passed
  - issues: `0`
  - parse failures: `0`
  - product status mismatches: `0`

### Tests and quality checks

```text
uv run pytest tests/integration/test_fresh_a_research_package.py -q
2 passed in 1.60s
```

```text
uv run ruff check src/ci_workflow/application/source_research_service.py src/ci_workflow/application/run_service.py
All checks passed!
```

```text
uv run mypy src/ci_workflow/application/source_research_service.py
Success: no issues found in 1 source file
```

### API smoke

Used `create_project_workspace(...)` and `run_project(...)` with the current package.

- Project:
  `research/a-real/smoke-project-r03-resolved`
- Run ID: `run_d1f9233fcfdb40441d6041a8`
- Outcome: `completed`
- Current-run manifest SHA:
  `25309ae5c6d3e4504cce347b39357633ee9875db8720107b151746db2e0a481d`
- HTML manifest SHA:
  `5b3dbbacb7d5eeb0292c06d67f8781bef68deb69d0dccea8d5e8f3f1c3149a1e`
- HTML artifact SHA:
  `efd16dc1524af0cfc7994c80ddbfb03d5d81ab0aee0b297bdd11473d9fc498f1`
- HTML artifact bytes: `30,129,241`
- HTML routes: `50`
  - Top-level routes: `12`
  - Product detail routes: `38`
- Nonempty routes: `true`
- Titles present: `true`
- Static HTML links: `855`
- Missing static HTML links: `0`

### CLI smoke

```text
uv run ci-workflow project run --root runs/acceptance/task-10.2-20260901-123524/research/a-real/cli-smoke-project-r03-resolved
项目运行完成。运行标识：run_515e9a1836b8946f99997141
```

- Project:
  `research/a-real/cli-smoke-project-r03-resolved`
- Run ID: `run_515e9a1836b8946f99997141`
- Outcome: `completed`
- Current-run manifest SHA:
  `5aaf3d2c688ed862a05859c6f3b8a43c40d19a3e17c3894250153e79fad36737`
- HTML manifest SHA:
  `88767579ef2b4509ec7a2296ea98d057a17185f0462766158e9b7a956df73b04`
- Input package SHA matched:
  `c196f67fadbafeb699dd682078a4044da4ea014b6d82ebfa8fcf0152f112bb90`
- HTML routes: `50`
- All routes nonempty: `true`
- Missing static HTML links: `0`

Both smoke manifests retain:

```text
render_verdict.status = rejected
render_verdict.anchor_ids = ["尚待独立浏览器验收"]
```

This is intentional. Technical generation passed; independent browser acceptance was not performed.

### Project verification

Both current smoke projects returned `PROJECT_OK` with contract version `1`.

## Blockers Or Missing Environment

- No local package-loader, source-lineage, cutoff, registry-projection, or technical-rendering blocker remains.
- Independent Chromium/WebKit acceptance was not run by this worker. Current-run render manifests remain rejected until Codex performs browser acceptance.
- PDF/PPTX acceptance was not run and no PDF/PPTX was generated.
- Wiley publisher content remained inaccessible; affected unsupported arm-level direct claims were excluded and the limitation is documented.
- NEJM publisher content remained inaccessible. The retained exact any-AE pair is explicitly caveated and must receive Codex scientific review.
- If Codex judges the retained NEJM pair insufficient, the draft MUST be blocked. No inferred substitute, composite, or zero may be introduced.

## Rerun Requests Or Next Step

1. Codex MUST use the current package digest
   `c196f67fadbafeb699dd682078a4044da4ea014b6d82ebfa8fcf0152f112bb90`.
2. Codex MUST run current-run Chromium and WebKit route acceptance against the newly generated HTML artifact:
   `efd16dc1524af0cfc7994c80ddbfb03d5d81ab0aee0b297bdd11473d9fc498f1`.
3. Codex MUST perform final independent scientific review, including:
   - NCT05509023 history-v10 arm identity and `未公开` TEAE/AESI sentinels.
   - NCT05608343 history-v12 efficacy/safety rows.
   - Wiley scoped-claim exclusions.
   - NEJM exact any-AE evidence sufficiency.
4. Any key-evidence insufficiency MUST block draft generation. No final PPTX or clinical acceptance is implied by this R03 completion.
