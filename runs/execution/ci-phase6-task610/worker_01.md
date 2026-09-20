# Execution Output: ci-phase6-task610 - worker_01

## Boundary And Context Check

- Scope limited to PNH B fixture data, three D70 fixture cases, catalog/schema registration, and the exact registration contract test.
- No Phase 6 publication, browser acceptance, or clinical/regulatory acceptance performed.
- No run-service implementation changes made.

## Work Performed

- Created `fixtures/positive/b-pnh/inputs/report-data.json`.
  - Two core trials: `APPLY-PNH` and `APPOINT-PNH`.
  - Treatment/control efficacy coverage.
  - Efficacy sentinels: `82.3`, `0.0`, `92.2`.
  - Typed efficacy, safety, baseline, and disposition views with source locators and disclosure states.
- Created physically isolated D70 inputs:
  - `fixtures/synthetic/b-d70-baseline-blocked/inputs/report-data.json`
  - `fixtures/synthetic/b-d70-baseline-recovered/inputs/report-data.json`
  - `fixtures/synthetic/b-d70-disposition-missing-pass/inputs/report-data.json`
- Added three D70 catalog entries to `fixtures/catalog.yaml`.
  - Expected states: `evidence_blocked`, `snapshot_locked`, `snapshot_locked`.
  - Distinct input hashes and case digests.
- Extended `schemas/fixture-case.schema.json` with the optional expected `state` enum.
- Added exact test:
  - `test_all_three_b_d70_cases_are_registered_hashed_and_have_distinct_expected_states`
- Corrected disposition fixture identity collisions; all disposition rows now have unique derived IDs.

## Artifacts And Evidence

Final D70 registration values:

- `b-d70-baseline-blocked`
  - Input SHA-256: `84d7fb369bd4aa508ef6ea4b0fdb4647d728c44f0a9eeac90db4cdd4441f66e0`
  - Case digest: `df7a678453bf37ba0caf042c50e636636052f06b08ee569f0a8bd98b4cda3d6c`
  - Baseline facts: `11`
  - Missing key: `nct04558918 / apply-treatment / age`
- `b-d70-baseline-recovered`
  - Input SHA-256: `13ca4d57178420eced06c3da0afa84cf2e8cd4de39b5101c33809168c4b54c01`
  - Case digest: `4f5f505d4b9328292f8a11f422dd1f5edaf653c140fdca75d3a86c803ef6309b`
  - Baseline facts: `12`
  - Restores exactly the missing age fact.
- `b-d70-disposition-missing-pass`
  - Input SHA-256: `078b520bf72f36ff85003c222b97ceca555f36436b960bb6d9a410a83eda75da`
  - Case digest: `cd9cf1b7ba76acec73d63fba6775f152cfe1954a6c9839a4d00ff0b046de0e54`
  - Baseline facts: `12`
  - Disposition facts: `54`
  - All disposition states: `not_publicly_disclosed`
  - Numeric values, numerators, denominators, and numeric raw expressions absent.

All four payloads contain:

- `3` typed efficacy facts.
- `12` typed safety facts.
- `54` disposition facts for D70 cases.
- Valid `ReportBPortalData`, baseline, disposition, efficacy, and safety models.
- Valid baseline and disposition JSON Schema instances.

## Commands And Observations

- `.venv/bin/python -m pytest -q tests/integration/test_fixture_case_contracts.py -k all_three_b_d70_cases_are_registered_hashed_and_have_distinct_expected_states`
  - Result: `1 passed, 3 deselected`.
- Typed model and JSON Schema validation passed for all four fixture packages.
- Baseline gate-binding smoke:
  - Recovered case: `12` bindings, no missing required units.
  - Blocked case: exactly one missing binding: `nct04558918 / apply-treatment / b_baseline_age`.
- View-builder smoke passed for all four packages:
  - Efficacy facts: `3`
  - Safety heatmaps: `4`
  - Baseline rows: `11` or `12` as intended
  - Disposition rows: `54`
- Static B renderer smoke passed:
  - `24` HTML files generated per package.
  - PNH rendered output contains `APPLY-PNH`, `APPOINT-PNH`, `82.3`, `92.2`, and `0.0`.
  - Disposition-missing output preserves `未公开` and contains no `0%` marker.

## Blockers Or Missing Environment

- System `python` executable is unavailable; `.venv/bin/python` works.
- Actual `run_fixture_case(..., reports=["B"])` execution was not performed; the B run-service adapter is outside this worker’s boundary and must be exercised after the owning implementation lands.
- Browser visual, clinical, and regulatory acceptance remain pending.

## Rerun Requests Or Next Step

- Run the three catalog cases end-to-end through the completed B run-service path.
- Run the fresh PNH B project path using `fixtures/positive/b-pnh`.
- Verify current-run manifest, snapshot, format/site artifacts, and delivery-ready status.
- Perform parent-level browser and final Phase 6 acceptance checks.
