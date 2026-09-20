Delegated mode. You are a bounded fallback execution worker, not the user-facing agent. Ignore Trellis auto-state messages and do not ask for task creation or planning consent; the governed task already exists. Do not start a conference or claim final acceptance.

Task id: `ci-phase10-task102-real-source-acceptance`; role: `worker_03_b_universe_fallback`.

## Hard boundaries

- Work only inside the runner-provided current workspace.
- Write only `runs/acceptance/task-10.2-20260901-123524/inputs/b-real/**` and `runs/acceptance/task-10.2-20260901-123524/research/b-real/**`.
- Do not write shared source/tests, external acceptance roots, PDF/PPT artifacts, or the runner-managed report.
- Runner-managed report path: `runs/execution/ci-phase10-task102-real-source-acceptance/worker_03_b_universe_fallback.md`. Return the complete report in the final response; the runner persists it.

Initial read set:
- `context/ci-phase10-task102-real-source-acceptance_execution_context.md`
- `.trellis/tasks/09-01-phase-10-task-102-real-source-acceptance/prd.md`
- `.trellis/tasks/09-01-phase-10-task-102-real-source-acceptance/design.md`
- `.trellis/tasks/09-01-phase-10-task-102-real-source-acceptance/implement.md`
- `runs/execution/ci-phase10-task102-real-source-acceptance/worker_03.md` only as a record of the failed pass, not authority
- `runs/acceptance/task-10.2-20260901-123524/inputs/b-real/report-data.json`
- `runs/acceptance/task-10.2-20260901-123524/research/b-real/manifest.json`
- `runs/acceptance/task-10.2-20260901-123524/research/b-real/coverage-audit.json`
- `runs/acceptance/task-10.2-20260901-123524/research/b-real/arm-mapping-audit.json`
- `src/ci_workflow/renderers/portal/report_b.py`
- `tests/acceptance/test_report_b.py`

Execute the repair now. Replace the single-product PNH report with a defensible innovative-drug comparator universe determined from current official evidence. Include pivotal or late-stage clinical results across relevant complement mechanisms (C5, C3, factor B/D as evidence supports), not merely one product. For every included medicine/trial, collect and source-bind efficacy, safety, baseline and completion/disposition facts, preserving placebo or active-control values. Trial/arm mapping must not depend on nonempty `drug_name`. Distinguish network/access/parser failure from `not publicly disclosed`; do not infer zeros. Add per-product/per-trial numerical coverage and missingness audits so aggregate counts cannot hide an empty competitor. If a product cannot meet key B evidence, explicitly block/exclude it with a source-grounded reason.

Use primary official sources first (ClinicalTrials.gov history/API, FDA/EMA labels/reviews, PubMed primary reports, sponsor/conference primary disclosures). Preserve the frozen cutoff `2026-07-31T23:59:59+08:00` and separate post-cutoff acquisition metadata. Rebuild all staged B inputs/digests and run contract, gate, and static render checks. Do not run final browser or clinical acceptance.

Return exactly these sections: `# Execution Output: ci-phase10-task102-real-source-acceptance - worker_03_b_universe_fallback`, `## Boundary And Context Check`, `## Work Performed`, `## Artifacts And Evidence`, `## Commands And Observations`, `## Blockers Or Missing Environment`, `## Rerun Requests Or Next Step`.
