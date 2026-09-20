# Execution Output: ci-rebaseline-rebuild-20260904 - worker_03

## Boundary And Context Check

- Worker boundary: `worker_03`, repository `.` only.
- No legacy external Chinese root, production environment, real host account, credentials, or runner report path was accessed or modified.
- Temporary render, bundle, install, and screenshot artifacts were written only under `/tmp` or tool-managed temporary directories.
- No RC commit/tag, real 8-indication research run, 24-portal matrix, or final clinical/regulatory/visual acceptance was claimed.

## Work Performed

- Added strict v1.3 intake and research-package contracts:
  - Public one-sentence `竞品调研` entry.
  - Native A/B/C type Ask when report type is omitted.
  - Optional historical cutoff.
  - Project-level, one-time Yaozh access decision without credentials/tokens.
  - Strict unknown-field, digest, locator, identity, and gate validation.
- Added typed application-owned Skill graph with independent ontology, identity, scientific, and package review nodes.
- Added universe-closure receipts covering global/China routes, alias, target, company, and trial reverse expansion, plus independent review/context.
- Added two-round heterogeneous recovery validation and explicit network-failure versus no-evidence distinctions.
- Changed manual inbox acceptance to:
  - Preserve the original file.
  - Record filename, SHA-256, DOI/PMID/registry identifiers, collision state, and target.
  - Rename atomically within the same directory.
  - Be idempotent on replay.
- Added required-publication classification and manual-supply gate behavior for primary, extension-primary, long-term, and safety evidence.
- Added B semantic construct validation covering:
  - Clinical construct and definition.
  - Direction, unit, estimand, denominator.
  - Analysis set/form.
  - Instrument/scale and actual timepoint.
  - Compatible near-window comparison and conflict rejection.
- Added exactly three neutral B bubble presets with explicit size semantics.
- Updated A/B/C portals:
  - Bottom external-source section on every rendered page.
  - Default-collapsed complete tables.
  - Shared source/table asset synchronization.
  - Removed user-facing evidence-maturity pages and radar-chart runtime paths.
  - Removed visible internal locator/backend fields from rendered tables.
- Rebased package surface to HTML-only:
  - Public manifest and schema.
  - CLI output validation.
  - Capability preflight with `independent_context`.
  - Explicit deferred-path bundle exclusions.
  - Removed `reportlab` from runtime dependencies and regenerated `uv.lock`.
  - Updated internal/public Skill wording and install guidance.
- Added/updated focused contract and integration tests for intake, package validation, closure, publication gates, inbox rename, B semantics, and portal behavior.

## G01-G18 Status

| Gate | Worker status | Evidence and residual |
|---|---|---|
| G01 | Targeted PASS | Public Skill, A/B/C Ask, one-sentence intake, cutoff, and strict package tests pass. |
| G02 | Targeted PASS | One-time Yaozh answer/route contract exists; no real Yaozh browser session was run. |
| G03 | Targeted PASS | `independent_context` is part of preflight and closure contracts; real independent reviewer availability was not supplied. |
| G04 | Targeted PASS | Universe closure receipt requires global/China routes, four expansion dimensions, and independent review; real multi-indication closure was not run. |
| G05 | Targeted PASS | Recovery-package and existing exhaustion/recovery regression tests pass; full real-source recovery was not run. |
| G06 | Targeted PASS | Required-publication classes, rule/model/reviewer coherence, one-response gate, limitation, and evidence-insufficiency behavior are implemented and tested. |
| G07 | Targeted PASS | Same-directory atomic rename, byte/digest preservation, collision failure, and replay idempotency are tested. |
| G08 | Targeted PASS | B semantic grouping and incompatible-construct guards are implemented and tested. |
| G09 | Targeted PASS | Exactly three B clinical bubble presets with size semantics are rendered and tested. |
| G10 | Targeted PASS | Rendered A/B/C fixtures produced 11/20/11 HTML pages; no user-facing maturity page was observed. Independent final visual acceptance remains pending. |
| G11 | Targeted PASS | Browser smoke confirmed chart/table disclosure behavior; full physical-page × viewport × engine coverage was not run. |
| G12 | Targeted PASS | Every rendered fixture page contained `#external-sources`; fixture-dependent external-link completeness remains to be checked against real source data. |
| G13 | BLOCKED | Full Chromium/WebKit Playwright matrix could not run because required browser executables are absent. |
| G14 | Candidate PASS | HTML-only package verification, bundle verification, and fresh install pass. Frozen Kangzhe design documents still contain historical `track_pdf`, `track_pptx`, and `htmlppt` references; they are contract documentation, not v1 delivery runtime. |
| G15 | Partial | `pypdf`/`pdfplumber` remain for research-document input; `reportlab` is removed. PDF acceptance checks were blocked by missing `pdftotext`. |
| G16 | Partial | Monitoring is excluded from the public manifest, CLI, and bundle runtime surface; full manual-refresh end-to-end execution was not run. |
| G17 | Partial | User-facing blocker/no-draft projection was updated and targeted behavior passes; independent acceptance across all report-level insufficiency cases remains pending. |
| G18 | Targeted PASS | HTML-only host contract and three-host semantic conformance tests pass; real Codex/Hermes/OMP external-process smoke was not run. |

## Artifacts And Evidence

- Final candidate bundle:
  - `/private/tmp/competitive-intelligence-workflow-0.1.0a0-final.tar.zst`
  - SHA-256: `f6faf63c147e45e3d787d116733f3f6b70772f09bb7173f00755ceebee99f533`
  - 310 declared files.
  - External manifest: `/private/tmp/competitive-intelligence-workflow-0.1.0a0-final.tar.zst.manifest.json`
  - External checksum: `/private/tmp/competitive-intelligence-workflow-0.1.0a0-final.tar.zst.sha256`
- Fresh isolated install:
  - `/tmp/ci-v1-final2-install-worker03.QP1DZP`
  - Installed entrypoint package verification returned `PACKAGE_OK`.
- Rendered browser smoke fixtures:
  - `/tmp/v1-portals-worker03/A`
  - `/tmp/v1-portals-worker03/B`
  - `/tmp/v1-portals-worker03/C`
- Browser screenshot:
  - `/var/folders/yb/31r9763x6_54mdxswxk36c4w0000gn/T/omp-sshots-157295f665496fa6.webp`
- Key source artifacts:
  - `src/ci_workflow/domain/research_package.py`
  - `schemas/research-package.schema.json`
  - `src/ci_workflow/application/intake.py`
  - `src/ci_workflow/graph/typed_skills.py`
  - `src/ci_workflow/capabilities/ontology_universe.py`
  - `src/ci_workflow/ingestion/publication_gate.py`
  - `src/ci_workflow/ingestion/manual_inbox.py`
  - `src/ci_workflow/reports/b/semantic_contract.py`
  - `src/ci_workflow/renderers/portal/report_a.py`
  - `src/ci_workflow/renderers/portal/report_b.py`
  - `src/ci_workflow/renderers/portal/report_c.py`
  - `src/ci_workflow/cli.py`
  - `tools/bundle_contract.py`
  - `package-manifest.json`
  - `schemas/package-manifest.schema.json`
  - `pyproject.toml`
  - `uv.lock`

## Commands And Observations

- `uv lock`
  - `Resolved 40 packages`.
- Final focused regression:
  - `63 passed in 5.07s`.
- Prior adjacent regression:
  - `80 passed in 4.33s`.
- Changed-module lint:
  - `uv run ruff check ...`
  - `All checks passed!`
- Python compilation:
  - `uv run python -m py_compile ...`
  - Exit 0, no output.
- JavaScript syntax checks:
  - `node --check` on changed source and mirrored portal assets.
  - Exit 0.
- Local package verification:
  - `PACKAGE_OK version=0.1.0a0 stage=development-candidate`.
- Bundle:
  - `BUNDLE_BUILT ... files=310`.
  - `BUNDLE_OK ... files=310 catalog=required-v12`.
- Fresh installed entrypoint:
  - `PACKAGE_OK version=0.1.0a0 stage=development-candidate`.
- Browser smoke observations:
  - A efficacy page: one chart, one table, one closed complete-table disclosure, one source section, no visible internal locator.
  - A global search Enter navigated to `products/dupilumab.html`.
  - B matrix: bubble chart, exactly three preset labels, one closed complete-table disclosure, one source section, no visible internal locator.
  - C overview: visible design matrix plus one closed chart-table disclosure, one source section, no maturity/internal locator text.
  - C 768px smoke: `scrollWidth=768`, `clientWidth=768`, no document-level horizontal overflow.
- Full repository test:
  - `464 failed, 2179 passed, 1 skipped, 60 errors`.
  - Failures were dominated by missing Playwright Chromium/WebKit executables and obsolete tests asserting the pre-v1.3 PDF/PPT/monitoring package contract.
- Non-browser grouped run:
  - `80 failed, 2128 passed, 1 skipped, 6 errors`.
  - Representative stale expectations include `phase-2-accepted`, PDF/HTML-PPT/PPTX selection, old capability IDs, old manual-inbox deletion, and old bundle-required governance files.

## Blockers Or Missing Environment

1. Playwright browser binaries are missing:
   - Chromium:
     `/Users/smkzw/Library/Caches/ms-playwright/chromium_headless_shell-1228/chrome-headless-shell-mac-arm64/chrome-headless-shell`
   - WebKit:
     `/Users/smkzw/Library/Caches/ms-playwright/webkit-2311/pw_run.sh`
2. `pdftotext` is unavailable, blocking legacy PDF text-verification tests.
3. No actual independent reviewer context was provisioned; runtime preflight intentionally fails closed without `CI_WORKFLOW_INDEPENDENT_CONTEXT=1`.
4. The candidate bundle is not bound to a clean RC commit/tag. Worker scope did not create commits or declare `RC_FROZEN`.
5. Historical frozen Kangzhe design-spec documentation remains in the bundle and contains old PDF/PPT route names/assets. Codex must decide whether the `legacy-absence` scanner treats these contract documents as disallowed.
6. Existing broad tests still contain pre-v1.3 expectations. They are not evidence that the current HTML-only contract is incorrect, but they prevent a green full-suite result until migrated or explicitly excluded.

## Rerun Requests Or Next Step

- Install the pinned Chromium and WebKit Playwright binaries, then rerun the complete A/B/C physical-page matrix across `1440×900`, `1024×1366`, `390×844`, and `320×568`.
- Provision a real independent reviewer/context and rerun closure and visual acceptance gates.
- Execute the Codex-owned clean-source RC build with source-commit provenance.
- Run the three real host smoke flows from the final installed bundle.
- Decide and document whether frozen design-spec historical files satisfy or violate the remaining `legacy-absence` owner gate.
- Do not emit `RC_FROZEN` or `RELEASED` from this worker result.
