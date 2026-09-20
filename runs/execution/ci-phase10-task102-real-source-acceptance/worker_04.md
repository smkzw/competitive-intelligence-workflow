# Execution Output: ci-phase10-task102-real-source-acceptance - worker_04

## Boundary And Context Check

- Wrote only:
  - `runs/acceptance/task-10.2-20260901-123524/inputs/c-real/**`
  - `runs/acceptance/task-10.2-20260901-123524/research/c-real/**`
- Did not modify production code, tests, final isolated acceptance root, runner-managed reports, PDF/PPT artifacts, or peer worker roots.
- Preserved cutoff: `2026-07-31T23:59:59+08:00`.
- Did not run final browser or clinical acceptance.

## Work Performed

Expanded the registry-first atopic-dermatitis universe from 4 trials / 3 products to:

- **20 Phase III pivotal or late-stage randomized trials**
- **12 products**
- **340 design observations**
- **5 mechanism classes**
- **3 routes**

Included trial IDs:

`NCT02260986`, `NCT04178967`, `NCT03985943`, `NCT05149313`, `NCT03131648`, `NCT03761537`, `NCT04146363`, `NCT03569293`, `NCT03607422`, `NCT03334396`, `NCT03745651`, `NCT04921969`, `NCT04773587`, `NCT04773600`, `NCT05032859`, `NCT05608343`, `NCT05398445`, `NCT05651711`, `NCT06130566`, `NCT06241118`.

Coverage spans:

- Cytokine pathways: IL-4Rα, IL-13, IL-31RA
- JAK pathway: JAK1 and JAK1/JAK2
- PDE4
- AhR
- OX40/OX40L T-cell costimulation
- Subcutaneous, oral, and topical routes

For every included trial:

- Product identity is bound to the official registry intervention entry.
- Target/mechanism metadata is linked to the same official registry record and precise intervention field path.
- Critical registry fields are populated:
  - target population
  - randomization/blinding/grouping
  - intervention and comparator arms
  - dosing regimen
  - primary endpoint definition
  - primary endpoint timepoint
- Per-product and per-trial coverage is explicit; sparse products cannot be hidden by aggregate totals.
- No cross-trial substitution is used.

`NCT06241118` uses official ClinicalTrials.gov history version 27 because the current version was posted after cutoff. The cutoff version reports the trial as recruiting with estimated enrollment of 636; those cutoff-bound values replace current post-cutoff values.

`NCT04345367` was excluded from the final one-product-per-trial universe because its active-comparator record binds both abrocitinib and dupilumab, creating ambiguous product ownership for this C portal contract. The exclusion and rationale are recorded in the coverage and research manifests.

## Artifacts And Evidence

Primary inputs:

- `inputs/c-real/report-c-data.json`
- `inputs/c-real/initial/report-c-data.json`
- `inputs/c-real/recovery/report-c-data.json`
- `inputs/c-real/source-receipts.json`
- `inputs/c-real/sources/clinicaltrials/*.json`

Research evidence:

- `research/c-real/research-manifest.json`
- `research/c-real/product-metadata.json`
- `research/c-real/registry-extracts.json`
- `research/c-real/coverage.json`
- `research/c-real/source-freshness.json`
- `research/c-real/gate-initial.json`
- `research/c-real/gate-recovery.json`
- `research/c-real/recovery-request.json`
- `research/c-real/supplement/recovery-manifest.json`
- `research/c-real/render-check.json`
- `research/c-real/html-preview/**`

Snapshot:

- `report_snapshot_id`: `c-real-expanded-snapshot-20260901-b80ce7118b14`

Source closure:

- 20 individual official registry JSON records
- No temporary search-response JSON remains in the registry source directory
- All selected records have first disclosure on or before cutoff
- Manifest artifact digests are closed with zero mismatches

## Commands And Observations

Gate and schema verification:

- Final payload model validation: passed
- Initial payload observations: `339`
- Recovered payload observations: `340`
- JSON Schema validation: `0` errors
- Initial gate: `blocked`
- Initial failure: exactly `c_missing_timepoint` for `nct06241118`
- Recovery gate: `passed`
- Nonblocking statistical gaps: `100` — five per trial, retained as `not_publicly_disclosed`

Coverage verification:

- Products: `12`
- Trials: `20`
- Observations: `340`
- Registry source records: `20`
- Per-product coverage rows: `12`
- Per-trial coverage rows: `20`
- All required critical fields present: `true`

Static render verification:

- Initial blocked render: `ReportCPortalError`, `0` HTML files
- Recovered render: `32` physical routes
  - 12 static pages
  - 20 trial detail pages
- Static page checks: passed
- Trial page checks: passed
- Chart/evidence identity binding: passed
- Chart before table: passed
- Chinese HTML and local asset checks: passed
- Browser checks: not run

Targeted source-contract tests:

```text
75 passed in 0.30s
```

## Blockers Or Missing Environment

No environment or network blocker.

Known renderer limitation is recorded transparently in `render-check.json`: the existing production renderer contains fixture-specific hard-coded population/eligibility phrase mappings. Exact registry excerpts for several expanded adult and pediatric trials are not accepted by that unmodified display normalizer.

Because production writes are outside this worker’s scope, the recovered HTML preview was generated with an in-memory display-only adapter. The adapter did not alter registry source text, observations, gate inputs, or evidence bindings. The preview static checks therefore passed, but unmodified production-renderer acceptance for these broader exact excerpts remains for Codex to decide.

## Rerun Requests Or Next Step

Codex should:

1. Review `research/c-real/research-manifest.json`, `coverage.json`, and `product-metadata.json`.
2. Copy the worker-owned `inputs/c-real` and `research/c-real` roots into the final isolated acceptance root.
3. Decide whether to retain the recorded display adapter limitation or make the minimum production renderer normalization repair.
4. Run final current-run exact acceptance, browser acceptance, and clinical/scientific review.
