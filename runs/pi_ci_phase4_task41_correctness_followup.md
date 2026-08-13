All verifications complete. Final report:

# Execution Output:

## Boundary And Context Check

- **SOUL.md full read: YES.** `/Users/smkzw/.hermes/SOUL.md` was read in full in this session's first turn (single complete file, no truncation), along with `AGENTS.md` and `context/ci_phase4_task41_context.md`. Also read the plan's Task 4.1 section (`../.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md`, read-only), the v1.2 spec (§15.3–15.7, §16.1, 附录 C, and full file), frozen A/B/C page catalogs, filter/format contracts, Phase 0 contract tests, Phase 3 snapshot/scientific-QC code and schemas.
- Working dir: `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`. No files written outside it; no wheel/venv artifacts left in repo (build/install material lived in `/tmp`, verified cleaned).
- All edits inside the Task 4.1 allowlist plus the followup's explicit additions: package-data copies of the frozen page catalogs under `src/ci_workflow/reports/common/page-catalogs/` and exact contract tests in the two authorized test files. Frozen originals (`docs/architecture/page-catalogs/*.yaml`), specs, plan, Trellis, context, prompts, runs, reviews, metrics, Phase 3 code, renderer/visual files untouched (git status confirms only `package-manifest.json` modified among tracked files — the pre-existing surgical schema-catalog entry).
- No commit/stage performed. `runs/pi_ci_phase4_task41_correctness_followup.md` not written by me (runner-owned; report returned here for persistence).
- Not self-accepting: Codex + independent verifier own acceptance.

## Work Performed

RED-first: wrote the attack/contract tests first and reproduced all five false-greens (exact suite pre-fix: **12 failed, 43 passed** — collision `derive_row_id(fact_id="x")==derive_row_id(claim_id="x")`, registry-omitted page responsibility accepted in both coverage and view validators, drifted filtered rows accepted, `PageRegistry._load_from_dir` missing, packaged catalogs missing). Then implemented:

1. **Mandatory page responsibility authority.** `validate_coverage_set_payload(raw)` now always loads the frozen `PageRegistry` (no `registry=` parameter on the public boundary); `check_coverage_set_semantics` takes a required registry; custom registries are injectable only via module-private `_validate_coverage_set_payload_with_registry`. `validate_report_view_model_payload` loads the frozen registry by default and rejects page responsibilities outside the matching report catalog (A rows labeled by B/C-only page IDs fail); internal test-only `_validate_report_view_model_payload_with_registry` exists. The chart/table validators enforce the same authority on embedded views (wrapped into `ChartTableBoundaryError`).
2. **Canonical filtered rows.** `FilteredRowSet` now requires each filtered row to be model-for-model equal (`row == canonical[view row]`) to the view's row for that ID — rejects disclosure-state flips, label rewrites, and snapshot/page drift while preserving genuine reorder/filter/empty (positive test included).
3. **Field-qualified row identity.** `derive_row_id` hashes `(field, value)` pairs in canonical field order via JSON material (escaped, no cross-field value collision, argument order irrelevant); added attacks across all adjacent identity field pairs.
4. **Installed PageRegistry.** Added byte-identical packaged catalog copies (`src/ci_workflow/reports/common/page-catalogs/{A,B,C}.yaml`, sha256-verified 1:1 with frozen originals); `PageRegistry.load()` resolves source-tree root docs → packaged layout automatically with no caller-selected production path (`root=` retained as test-only); `_load_from_dir` is the shared loader. Built a real wheel, inspected all three catalog members, installed into a fresh 3.13 venv, proved `load()` returns A/B/C, sitemap expansion, and that coverage/view production validators (packaged schemas + packaged registry) work and reject out-of-catalog pages; installed catalogs byte-identical to frozen originals.
5. **Lookup boundary documented and bound.** Row contract is: rows carry stable immutable fact/claim/product/… identities only, no duplicated clinical values; consumers resolve values exclusively through the locked `report_snapshot_id`. Mechanically bound by (a) single-snapshot/single-page binding at row/view/module level, (b) canonical row equality so no layer can substitute content or swap snapshots, (c) frozen-catalog page authority. Documented in `view_state.py` and `chart_specs.py` docstrings. No Task 4.4 chart-compatibility or domain-specific efficacy/safety fields added.

## Artifacts And Evidence

- `src/ci_workflow/reports/common/view_state.py` — field-qualified `derive_row_id`, frozen-catalog authority in production validator, internal test-only registry path, lookup-boundary docstring.
- `src/ci_workflow/reports/common/chart_specs.py` — canonical row equality in `FilteredRowSet`, catalog authority on embedded views.
- `src/ci_workflow/reports/common/coverage.py` — mandatory-registry semantics, public validator always loads frozen registry, `_validate_coverage_set_payload_with_registry` internal path.
- `src/ci_workflow/reports/common/page_registry.py` — dual-layout `load()` (source-tree → packaged), `_load_from_dir`, `_search_paths`.
- `src/ci_workflow/reports/common/page-catalogs/{A,B,C}.yaml` — package-data copies, byte-identical (contract test + sha256 cross-check: every root hash appears exactly twice).
- `tests/unit/reports/test_view_model.py` — 8 new nodes (identity field-qualification ×2, frozen-catalog authority ×3, canonical drift ×2, packaged layout ×1).
- `tests/contract/test_coverage_set.py` — 5 new nodes (no-registry attacks ×2, internal-registry path ×1, packaged catalog byte-equality ×1, packaged layout load ×1); helpers parameterized by report.
- Schemas unchanged (already expressed representable structure; semantic rules documented as validator-enforced); `package-manifest.json` entry unchanged from prior session.

## Commands And Observations

- **RED** (exact suite, pre-implementation): `uv run pytest tests/unit/reports/test_view_model.py tests/contract/test_coverage_set.py -q` → `12 failed, 43 passed`; every failure mapped to a named false-green.
- **Each new attack node individually**: 13/13 `1 passed` (8 in test_view_model.py, 5 in test_coverage_set.py).
- **Exact two planned files**: `uv run pytest tests/unit/reports/test_view_model.py tests/contract/test_coverage_set.py -q` → `55 passed in 0.85s` (55 PASSED with `-v`).
- **Phase 0 + Phase 3 regressions**: `tests/contract/test_page_catalogs.py test_filter_contracts.py test_format_contracts.py test_package_manifest.py test_scientific_qc_verdict_contract.py tests/integration/test_snapshot_identity.py test_scientific_qc_gate.py tests/graph/test_scientific_qc_isolated_veto.py` → `32 passed`.
- **Ruff** (changed files): `uv run ruff check src/ci_workflow/reports/ tests/unit/reports/ tests/contract/test_coverage_set.py` → `All checks passed!`. Repo-wide `ruff check .` reports 284 pre-existing errors, all in `.trellis/scripts/` and host hooks (`.codex/.cursor/.codebuddy/hooks`) — zero in Task 4.1 files.
- **Strict mypy**: `uv run mypy src/ci_workflow/reports/ --strict` → `Success: no issues found in 5 source files`.
- **Schema checks**: Draft 2020-12 `check_schema` + packaged-copy byte-equality covered inside the contract suites above (passed).
- **Package verify**: `uv run ci-workflow package verify --root .` → `PACKAGE_OK version=0.1.0a0 stage=phase-2-accepted`.
- **Wheel isolation**: `uv build` wheel contains `ci_workflow/reports/common/page-catalogs/{A,B,C}.yaml` (6172/10907/5901 bytes) + both coverage schemas; fresh 3.13 venv install → `PageRegistry.load()` → `['A','B','C']`, sitemap expands `/a/products/product-01|product-02` and `/a/trials/trial-01` (len 14 = 11 static + 3 dynamic), coverage + view validators accept valid payloads and reject `baseline-demographics` in an A set/view (installed layout), installed catalogs byte-identical to frozen originals. Temp venv/build dirs removed (grep count 0).
- **`git diff --check`**: OK.
- **Full pytest**: `uv run pytest -q` → **527 passed in 70.69s** (464 Phase 3 baseline + Task 4.1).

## Blockers Or Missing Environment

- None. All required verification steps completed with named outputs; the only env quirk was that plain `pip` in a system-3.9 venv cannot resolve this repo's future-pinned deps (playwright 1.61.0 / jsonschema 4.26.0), so the wheel-isolation proof used a `uv`-created Python 3.13 venv with `--no-deps` + the three runtime deps — this is a sandbox mirror limitation, not a package defect.
- Note for acceptance: `PageRegistry.load(root=...)` and `_validate_*_payload_with_registry` remain as the explicit test-only paths; production entry points never accept caller-selected paths/registries.

## Rerun Requests Or Next Step

- No rerun required. Deliverable is complete: 13/13 new nodes green individually, exact suite 55/55, Phase 0 + Phase 3 bindings 32/32, full suite 527/527, Ruff/mypy/package/diff clean, wheel isolation proven end-to-end with installed-layout behavior identical to source tree.
- Next step for Codex (final authority; not self-accepted here): re-run the acceptance commands in a fresh context (individual attack nodes, exact two files, Phase 0/3 regressions, Ruff, strict mypy, package verify, wheel install proof, full pytest, `git diff --check`), then launch the independent verifier against the anchors above. Runner: persist this report to `runs/pi_ci_phase4_task41_correctness_followup.md`. No commit was made, per boundary.
