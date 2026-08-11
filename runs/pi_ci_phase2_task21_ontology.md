# Task 2.1 Independent Verification

I read the full SOUL.md file (267 lines; the first read truncated the tail in display, so I re-read lines 230–267 to cover the remainder) and complied with its delegation contract: read-only verification, no edits, Codex remains final authority.

## Boundary And Sources Read

Read only within `competitive-intelligence-workflow`. All 13 mandated sources read in full:

- `context/ci_phase2_task21_ontology_context.md`
- `.trellis/tasks/08-11-phase-2-universe-source-truth/{prd.md,design.md,implement.md}`
- `docs/decisions/0006-phase-2-universe-and-source-boundaries.md`
- `policies/ontology/innovation-therapy-v1.yaml` (raw)
- `src/ci_workflow/capabilities/ontology_universe.py` (raw, full — initial reads were elided summaries)
- `tests/unit/test_innovation_eligibility.py`, `tests/unit/test_regimen_eligibility.py` (raw)
- `tests/contract/test_package_manifest.py` (raw)
- `package-manifest.json` (raw)
- `docs/acceptance/runs/task-2.1/{red.txt,green.txt}` (raw)

Supporting repo context (for command reconstruction and provenance, not Task 2.1 claims): `pyproject.toml`, `src/ci_workflow/domain/ids.py`, `src/ci_workflow/capabilities/__init__.py`, `src/ci_workflow/cli.py` (grep), `metrics/ci_phase2_task21_ontology_metrics.md`, git state. No files edited; temp RED archive removed; git status unchanged at 15 entries.

## Commands Reproduced

**GREEN — four exact nodes, individually** (each `1 passed`, matching green.txt):
- `uv run pytest tests/unit/test_innovation_eligibility.py::test_innovation_modalities_include_adc_and_fusion_protein -q` → 1 passed
- `…::test_unmatched_reformulation_repositioning_or_fixed_combination_stays_review_pending` → 1 passed
- `…::test_innovative_plus_traditional_background_includes_regimen_without_promoting_background_component` → 1 passed
- `…::test_pure_traditional_regimen_is_excluded` → 1 passed

**RED — independently reproduced at HEAD**: `git archive HEAD` into an isolated dir, copied only the four test files in, forced archive `src` onto `PYTHONPATH` (the editable install otherwise leaked the current module). Result: exactly 4 failed, each `ModuleNotFoundError: No module named 'ci_workflow.capabilities'` — matching red.txt's "failed because `ci_workflow.capabilities.ontology_universe` did not exist" (HEAD `git ls-files` confirms no `capabilities/`). Archive removed afterward.

**Suites**:
- Combined Task 2.1: `uv run pytest tests/unit/test_innovation_eligibility.py tests/unit/test_regimen_eligibility.py` → **4 passed** (matches record)
- + package contract: **5 passed** (matches record)
- Full repo: `uv run pytest` → **137 passed** in 6.4s (matches record)
- Ruff: `uv run ruff check src tests/unit/test_innovation_eligibility.py tests/unit/test_regimen_eligibility.py tests/contract/test_package_manifest.py` → **All checks passed**
- Strict mypy: `uv run mypy src` → **Success: no issues found in 22 source files**
- Package: `uv run ci-workflow package verify --root .` → **PACKAGE_OK version=0.1.0a0 stage=phase-0-task-0.4**
- `git diff --check` → clean

## Contract And False-Green Audit

Audited against ADR 0006 + policy + production code, with runtime adversarial probes:

- **Free-text fallback**: none. `evaluate_component` matches `modality.casefold()` exactly against policy keys, with whitespace-only normalization. Probes: `单克隆抗体`, `单抗`, `Antibody-Drug Conjugate`, `抗组胺药` all → `review_pending` (fail-safe), never silently included/excluded by name, marketing wording, or similarity. `'ADC'`/`'adc '` → included (casefold + blank-normalization only).
- **Traditional background promotion**: `evaluate_regimen` puts only `included` components in `competitor_component_ids`/`competitor_profile_component_names`; `innovation_component_count=len(included)`; `regimen_count=1` only with ≥1 included and no pending. Traditional component stays `excluded` (asserted). No promotion.
- **Pure-traditional inclusion**: no included, no pending → `excluded`, `regimen_count=0`, empty competitor ids. Safe.
- **Pending silently excluded**: pending → regimen `review_pending` with explicit "宇宙暂不能闭合" reason; `close_competitor_universe` returns `universe_closed=False` and `allowed_downstream_nodes=()` — gate/snapshot/render all blocked.
- **Closure before evidence-bound review**: `review_boundary` is the only sanctioned path to resolve a pending item and raises unless `review_pending` and no existing receipt; receipt requires `reviewer_id`, `rationale`, `rule_version`, `evidence_fragment_ids` (min 1), and tz-aware `reviewed_at`. Post-review close verified in test (`universe_closed=True`, nodes restored).
- **Mutable/incomplete audit fields**: all models `frozen=True`, `extra="forbid"`, tuple-typed; `audit_records` immutable; rule hits carry `rule_id`/`rule_version`/`reason_zh`/evidence ids. No false-green via mutation.
- **Policy/migration omission**: `components.policies == ["policies/ontology/innovation-therapy-v1.yaml"]` asserted in the contract test (passes) and matches disk exactly (glob confirms no drift); `migrations/0008_project_lineage_guards.sql` present and asserted; manifest schema-validated; `package verify` passes. Policy version literals (`schema_version/policy_id/version` = 1.0) enforced by pydantic `Literal`.
- **Stable IDs / no Top-N**: `stable_id` SHA-256 deterministic; `regimen_id` composes component ids; no truncation logic exists in the module.
- Acceptance records internally consistent with independent reproduction (RED ×4 missing-module, GREEN ×4 pass, 4/5/137 counts).

## Findings

**P0 = 0. P1 = 0. P2 = 0. P3 = 3** (informational, none blocking):

1. **P3** — Repo-wide `ruff check .` (35 diagnostics: `.codebuddy/hooks/inject-shell-session-context.py`, `tools/*`) and `mypy .` (61 diagnostics in 6 files: `tests/integration/*`, `tests/contract/test_artifact_manifest.py`, `tests/unit/test_state_enums.py`) fail on files tracked at HEAD (last touched 298cbe2, pre-Task-2.1) and untouched by the Task 2.1 diff (3 modified + untracked additions). Task 2.1 scope is clean; the record's "Ruff, strict mypy passed" is only reproducible as scoped (`src` + Task 2.1 tests). Pre-existing debt, not a Task 2.1 regression.
2. **P3** — `close_competitor_universe`/`review_boundary` have no production callers yet (wiring lands in Task 2.2+); reviewer independence is a process contract (free-text `reviewer_id`), not machine-enforced.
3. **P3** — A resolved pending item keeps `rule_id="review-unmatched-boundary"` after `review_boundary` flips the decision; resolution is carried by `decision` + receipt, so not a correctness gap, but the label can mislead auditors. Also `metrics/ci_phase2_task21_ontology_metrics.md` remains a TODO stub (process artifact, not acceptance evidence).

## Verdict

**PASS** — P0=0, P1=0. All four exact nodes independently reproduce RED (missing module) and GREEN (pass) for the intended reasons; combined suite 4/5 pass, full repo 137 pass, Task 2.1-scoped Ruff and strict mypy pass, `package verify` and `git diff --check` pass. No false-green path found in policy or production code: no free-text/name-based inclusion, no traditional-component promotion, no pure-traditional entry, no silent pending-item resolution, closure blocked while any item awaits evidence-bound review, audit fields immutable and complete, policy registered in the packaged manifest.

## Codex-Owned Final Checks

- Clinical/regulatory correctness of the policy's modality boundaries (which modalities are truly "innovative") — not verifiable from code; needs domain authority.
- Repo-wide static debt (P3-1) — decide whether to schedule cleanup or scope CI to `src`.
- Later tasks must wire `close_competitor_universe`/`review_boundary` with all components of all regimens so no pending item bypasses closure; reviewer independence needs an enforcement mechanism at the ingestion/service layer.
