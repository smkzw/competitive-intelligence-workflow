# Execution Output: ci-phase10-task102-real-source-acceptance - worker_03_b_universe_fallback

## Boundary And Context Check

- Worker writes stayed within the permitted B input/research paths.
- Shared source, tests, PDF/PPT artifacts, external acceptance roots, and runner-managed report were not modified.
- Frozen cutoff preserved: `2026-07-31T23:59:59+08:00`.
- Post-cutoff acquisition metadata separated at `2026-09-01T14:30:00+08:00`.

## Work Performed

- Replaced the single-product package with 5 products and 6 pivotal/late-stage trials covering factor B, C3, factor D, and C5.
- Preserved placebo/active-control values within each trial; controls were not promoted to independent products.
- Added source-bound efficacy, safety, baseline, and disposition facts.
- Added explicit `not_publicly_disclosed` rows without inferred zeros.
- Added per-product/per-trial coverage and missingness audits.
- Added arm mappings based on source arm labels/registry identity, with `drug_name_dependency:false`.
- Explicitly excluded:
  - `pozelimab + cemdisiran`, NCT05131204: terminated; insufficient complete comparable key evidence.
  - BCX9930, NCT05116787: phase 2 halted/terminated; no pivotal late-stage comparator evidence.
- Added 16 official-web source extracts and retained the existing iptacopan sources.
- Removed the one-shot rebuild helper after completion.

## Artifacts And Evidence

- [B report data](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/runs/acceptance/task-10.2-20260901-123524/inputs/b-real/report-data.json>)
- [Universe decision](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/runs/acceptance/task-10.2-20260901-123524/research/b-real/universe-decision.json>)
- [Coverage audit](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/runs/acceptance/task-10.2-20260901-123524/research/b-real/coverage-audit.json>)
- [Arm-mapping audit](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/runs/acceptance/task-10.2-20260901-123524/research/b-real/arm-mapping-audit.json>)
- [Missingness diagnosis](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/runs/acceptance/task-10.2-20260901-123524/research/b-real/missingness-diagnosis.json>)
- [Source inventory](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/runs/acceptance/task-10.2-20260901-123524/research/b-real/source-inventory.json>)
- [Run evidence](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/runs/acceptance/task-10.2-20260901-123524/research/b-real/run-evidence.json>)
- [Package manifest](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/runs/acceptance/task-10.2-20260901-123524/research/b-real/manifest.json>)
- [Static smoke overview](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/runs/acceptance/task-10.2-20260901-123524/research/b-real/static-render-smoke/overview.html>)

Representative official sources include [ClinicalTrials.gov NCT04434092](https://clinicaltrials.gov/study/NCT04434092?tab=results), [FDA Piasky review](https://www.accessdata.fda.gov/drugsatfda_docs/nda/2024/761388Orig1s000IntegratedR.pdf), [FDA Voydeya snapshot](https://www.fda.gov/drugs/drug-trials-snapshots/drug-trials-snapshots-voydeya), and primary reports for [PEGASUS](https://pubmed.ncbi.nlm.nih.gov/33730455/) and [CHAMPION-301](https://pubmed.ncbi.nlm.nih.gov/30510080/).

Final staged counts: 5 products, 6 trials, 33 efficacy rows, 51 safety rows, 46 baseline rows, 145 disposition rows, 27 inventoried sources, 81 manifest records.

## Commands And Observations

- Rebuild command executed successfully:
  `PYTHONPATH=src .venv/bin/python .../research/b-real/rebuild_b_universe.py`
- Rich model validation passed for all four fact domains.
- `ReportBPortalData` validation passed.
- Baseline gate failures: none.
- Static renderer produced 32 B routes; smoke digest:
  `79236f88363dc544726d4eff61a83304c5b71612827c1e626e00047786cdd607`
- Focused tests: `12 passed`.
- Manifest hash/size/mtime verification: passed with no stale records.
- Final state remains `research_ready_html_pending`; `html_generated:false`.

## Blockers Or Missing Environment

- Direct shell retrieval failed because configured proxy `127.0.0.1:7897` refused connections and direct DNS also failed. This was recorded as a technical route failure, not evidence absence; official web routes supplied the captured evidence.
- Danicopan’s public baseline source provides an eligibility Hb threshold, not observed group means. The threshold and explicit missing observed-value rows are both preserved.
- Some danicopan and crovalimab completion/disposition fields remain explicitly not publicly disclosed.
- Final browser and clinical/regulatory acceptance were not run by this worker.

## Rerun Requests Or Next Step

Controller/Codex should consume the staged B package, run the B HTML pipeline, bind the immutable report snapshot, and perform final browser plus clinical acceptance. No worker rerun is needed unless the comparator universe or source evidence changes.
