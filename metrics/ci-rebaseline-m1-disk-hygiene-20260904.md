# M1 Disk-Hygiene Receipt: ci-rebaseline-rebuild-20260904

Date: 2026-09-04 16:20 CST

## Decision

After the R0/R1 gate and independent conference evidence were durable, Codex removed only repository-local, reproducible interpreter/test/type-check caches identified by an exact pre-delete inventory. No scientific evidence, fixture, report, browser receipt, conference artifact, normative document, package input, virtual environment, recovery manifest or recovery point was deleted.

## Pre-delete Inventory

- Authorized workspace: current English-path repository only.
- Exact initial target count: 54 unique directories.
- Direct target allocation: 53,368 KiB (54,648,832 bytes).
- Whole-workspace allocation before cleanup: 5,849,544 KiB.
- The forbidden legacy root was neither named to nor inspected by an inventory command.

## Removed Targets

```text
.mypy_cache
.pytest_cache
.ruff_cache
.trellis/scripts/common/__pycache__
contracts/kangzhe/design_specs/tests/__pycache__
runs/tests/task64/__pycache__
src/ci_workflow/__pycache__
src/ci_workflow/application/__pycache__
src/ci_workflow/capabilities/__pycache__
src/ci_workflow/domain/__pycache__
src/ci_workflow/gates/__pycache__
src/ci_workflow/graph/__pycache__
src/ci_workflow/graph/definitions/__pycache__
src/ci_workflow/hosts/__pycache__
src/ci_workflow/ingestion/__pycache__
src/ci_workflow/qc/__pycache__
src/ci_workflow/renderers/__pycache__
src/ci_workflow/renderers/html_ppt/__pycache__
src/ci_workflow/renderers/html_ppt/projections/__pycache__
src/ci_workflow/renderers/pdf/__pycache__
src/ci_workflow/renderers/pdf_native/__pycache__
src/ci_workflow/renderers/pdf_native/projections/__pycache__
src/ci_workflow/renderers/portal/__pycache__
src/ci_workflow/renderers/pptx_master/__pycache__
src/ci_workflow/reports/a/__pycache__
src/ci_workflow/reports/b/__pycache__
src/ci_workflow/reports/c/__pycache__
src/ci_workflow/reports/common/__pycache__
src/ci_workflow/schemas/__pycache__
src/ci_workflow/sources/__pycache__
src/ci_workflow/sources/connectors/__pycache__
src/ci_workflow/storage/__pycache__
tests/acceptance/__pycache__
tests/browser/__pycache__
tests/contract/__pycache__
tests/fixtures/task44-chart-table-sync/__pycache__
tests/fixtures/task45-evidence-drawer/__pycache__
tests/graph/__pycache__
tests/hosts/__pycache__
tests/html_ppt/__pycache__
tests/integration/__pycache__
tests/integration/reports/__pycache__
tests/integration/sources/__pycache__
tests/migration/__pycache__
tests/pdf/__pycache__
tests/renderers/__pycache__
tests/reports/__pycache__
tests/reports/a/__pycache__
tests/reports/b/__pycache__
tests/reports/c/__pycache__
tests/unit/__pycache__
tests/unit/reports/__pycache__
tests/unit/reports/a/__pycache__
tools/__pycache__
```

## Post-delete Verification

- Task/Trellis validation recreated `tools/__pycache__` and `.trellis/scripts/common/__pycache__`; those same two already-authorized paths were removed again after validation, reclaiming another 216 KiB. Total removal events: 56 over 54 unique paths.
- Remaining directories matching the same exact cache classes outside `.venv`: 0.
- Whole-workspace allocation after cleanup: 5,795,152 KiB.
- Observed whole-workspace decrease in the first sweep: 54,392 KiB. The conservative sum of direct target allocations is 53,584 KiB (54,863,872 bytes) across both sweeps; this is the reported reclaimed amount. Normative receipts added between measurements are retained and are not netted against cleanup.
- `.venv` was intentionally retained as the reproducible locked execution environment; its internal bytecode caches were not targeted.
- `.playwright-cli`, conference logs/reports, historical archives, unaccepted reports, fixtures, source evidence, manifests, receipts and the previous read-only recovery point were retained.

## Recovery

The removed directories contain no authoritative source. They are recreated by the relevant Python, Ruff, mypy or pytest invocation. The previous read-only full recovery point also preserves the pre-cleanup repository state.
