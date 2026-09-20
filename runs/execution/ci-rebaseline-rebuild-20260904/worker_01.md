# Execution Output: ci-rebaseline-rebuild-20260904 - worker_01

## Boundary And Context Check

- R0 scope only. No R1 canonical documents or Task 10.6 documents modified.
- External legacy root was not read, inventoried, chmod-ed, or modified.
- Current repository remained dirty. No staging, commit, reset, checkout, clean, or unrelated deletion performed.
- Runner report path was not written; this response is the worker report.

## Work Performed

- Captured immutable pre-change inventory before worker edits:
  - 6,599 status entries: 66 modified, 6,533 untracked.
  - HEAD: `bb27ec9d750cf02fb64da5dfe665b2f4b262922d`
  - Inventory digest: `5c7a5973dee9dbba7cea7e30daba283803d8bdd57b15451da85749f3c0c0550b`
- Established two explicit content-addressed source sets from `tools/bundle_contract.py:DEFAULT_ALLOWLIST`:
  - Original pre-repair baseline retained unchanged.
  - Postquality source set generated after repairs.
- Added fail-closed governance tools:
  - `tools/check_clean_tree.py`
  - `tools/verify_rebaseline_source_set.py`
  - `tools/gate.sh`
- Repaired internal typing and lint defects across HTML-PPT, portal, PDF-native, PPTX, C-report, source-research, and run-service code.
- Added justified ReportLab boundary ignores; no broad typing suppression.
- Fixed stale HTML-PPT runtime contract assertion and test import/format violations.
- Added focused provenance and gate tests covering:
  - clean, staged, untracked, and allowlisted Git states;
  - repository-root enforcement;
  - source-set digest tampering;
  - malformed source-set paths;
  - dirty release provenance.

## Artifacts And Evidence

- `context/ci-rebaseline-rebuild-20260904_prechange_inventory.json`
  - Status SHA-256: `6ae1d16633e2e67dd900e907134a5ef1154399b8e7d0f6cce59bb9490c81d60c`
  - Tracked-index SHA-256: `a48d8045e9742260397c6bc048250f3f9c4f0a968596b9b64972c8783c0c8854`
- `docs/governance/rebaseline-release-source-set-v1.json`
  - Immutable pre-repair baseline.
  - Source-set SHA-256: `9e935dfe9b84cae6d3f223a9269fbddf281128d3d1564254438f9468c3c4ad4f`
- `docs/governance/rebaseline-release-source-set-v1-postquality.json`
  - 28 explicit roots, 422 regular files.
  - Source-set SHA-256: `7c0639045a0b0a8c87369a5308ba25432e3ca4cb9f7720f6c972aef09aa27a01`
- `docs/governance/r0-provenance-and-quality-gate.md`
- `tests/contract/test_rebaseline_governance.py`
- Baseline evidence:
  - Initial mypy failure: `artifact://6`
  - Initial Ruff failures: `artifact://4`
  - Initial stale contract test failure: `artifact://15`
  - Initial clean-tree fail-closed result: `artifact://29`
  - Final strict mypy ReportLab-stub limitation: `artifact://83`

## Commands And Observations

Final consolidated gate:

```text
bash tools/gate.sh --source-set \
  docs/governance/rebaseline-release-source-set-v1-postquality.json
```

Observed:

- Ruff: passed for `src tests tools`.
- Mypy: passed for `src tools`, 190 files, using the declared `--ignore-missing-imports` boundary.
- Unit and contract tests: `857 passed`.
- Legacy-reference check: `LEGACY_REF_OK`.
- Source-set verification: `SOURCE_SET_OK files=422`.
- Final result: `GATE_OK status=quality-only steps=5`.

Focused governance tests:

```text
uv run pytest tests/contract/test_rebaseline_governance.py -q
3 passed
```

Raw strict typing remains non-green:

```text
uv run mypy --no-incremental src tools --show-error-codes
```

- 31 ReportLab `import-untyped` errors across 10 files.
- `reportlab-stubs` / `types-reportlab` is not installed.
- No dependency was silently installed.
- This limitation is explicitly documented; the gate does not claim full strict typing.

Release cleanliness check:

```text
uv run python tools/verify_rebaseline_source_set.py \
  docs/governance/rebaseline-release-source-set-v1-postquality.json \
  --require-clean
```

Observed fail-closed result:

```text
SOURCE_SET_FAIL 来源集合要求 clean commit，但工作树存在改动
```

The repository is quality-green under the declared environment boundary, but not release-ready because the source tree remains dirty.

LSP reference lookup was attempted for the exported eligibility projection symbol, but only the Ruff server was available and the references endpoint returned `Unknown request: textDocument/references`. Repository search, mypy, and tests covered the affected callsites.

## Blockers Or Missing Environment

- Release commit provenance is blocked by the intentionally preserved dirty tree.
- Full raw strict mypy is blocked by missing ReportLab typing stubs.
- No legacy-root verification was performed by design and policy.

## Rerun Requests Or Next Step

1. An authorized owner selects and commits the intended grouped release snapshot.
2. Rerun:

```text
bash tools/gate.sh --require-clean --source-set \
  docs/governance/rebaseline-release-source-set-v1-postquality.json
```

3. Provide or pin ReportLab typing stubs, then rerun raw strict mypy before claiming full strict-type acceptance.
