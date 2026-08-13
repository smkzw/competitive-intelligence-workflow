# Execution Output:

## Boundary And Context Check

- Working dir: `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`. No writes outside it.
- Files changed this round (Task 3.7 allowlist + directly affected source/tests):
  1. `src/ci_workflow/storage/event_store.py` — public-append guard, `AuthorizationAppendForbiddenError`, module-private `_AuthorizationAppendCapability`/`_AUTHORIZATION_APPEND_CAPABILITY`, `_append_authorization` (capability path) + `_append` (shared impl) split.
  2. `src/ci_workflow/graph/executor.py` — capability import; `_issue_scientific_qc_authorization` routes issuance through `self.store._append_authorization(event, _AUTHORIZATION_APPEND_CAPABILITY)`. All other append call sites (transitions, node completion, run/recovery/inbox events) untouched.
  3. `src/ci_workflow/capabilities/scientific_qc.py` — `_scientific_qc_verdict_schema()` resolver (source-tree + packaged-install layouts), production validator `validate_scientific_qc_verdict_payload()` (Draft 2020-12 → Pydantic → semantic, deterministic errors), `_revalidate_verdict` now delegates to it.
  4. `tests/integration/test_scientific_qc_gate.py` — §34 rewritten (public-append rejection before storage + tampered-file reducer/replay), +3 new attack tests.
  5. `tests/contract/test_scientific_qc_verdict_contract.py` — new contract test calling the same production validator (4 tests).
- No specs/plans/Trellis/context/prompts/review/metrics files edited. No commit/stage. Report not written (runner-owned). Prior rounds' preserved paths (candidate-digest binding, one-time consumption + epoch, no-downstream veto, typed node output) rechecked in-suite, all green.

## Work Performed

**Finding 1 — public `EventStore.append` remained forgeable (closed at ingress).** `boundary_proof_digest` was recomputed solely from serialized payload fields in `reducer.py`, so an ordinary caller computing the correct digest could append directly. Fix is mechanical:
- `EventStore.append()` rejects `event_type == "scientific_qc.authorization.issued"` **unconditionally, before storage and before dedup**, with deterministic `AuthorizationAppendForbiddenError` ("科学质控授权事件只能由质控边界经专用路径签发").
- Private `EventStore._append_authorization(event, capability)` requires the opaque module-private `_AuthorizationAppendCapability` singleton checked by identity (`is`); wrong event type on the specialized path also rejected. No public factory/alias exists (`hasattr` assertions in test).
- Only `GraphExecutor._issue_scientific_qc_authorization()` receives/uses the capability.
- Persisted replay still validates full deterministic payload/event ID/evidence/epoch/proof digest; §34 now proves a tampered on-disk record (correct `event_digest`, wrong `boundary_proof_digest`) fails both `graph_reducer` and `CheckpointStore.replay`.
- Honest limit documented in code and tests: Python private symbols are not hostile-process security; the contract is public-API provenance correctness.

**Finding 2 — `_revalidate_verdict` lacked Draft 2020-12 (closed).** Prior claim "same boundary" was false; now one production validator runs, in order: packaged `schemas/scientific-qc-verdict.schema.json` Draft202012 → Pydantic `ScientificQcVerdict` → `check_scientific_qc_verdict_semantics`, each failure a deterministic `ScientificQcBoundaryError`. `_revalidate_verdict` calls it. Schema path resolves source tree (`parents[3]/schemas`) and packaged-install layout (`parents[1]/schemas` = `ci_workflow/schemas/` package data); no caller-selected path parameter; deterministic fail-closed error when both missing. Negative payload that Pydantic/semantic alone accept but schema rejects: `locators[0].locator.page = true` (Pydantic lax-coerces `True→1`; semantic passes; schema rejects `integer`). Public `apply_scientific_qc_verdict` rejects with "打包 Schema" **before any authorization write** (`executor.store.read_all() == ()` asserted). Contract test calls the same validator under both layouts (simulated install tree) and asserts deterministic error equality.

Rechecked and still closed: one-time consumption + epoch (SQ01 §35, isolated-veto suite), nested SourceRef locator uniqueness/binding (SQ02 nested-dup/unbound assertions).

## Artifacts And Evidence

- `event_store.py` — `AuthorizationAppendForbiddenError`; `_QC_AUTHORIZATION_EVENT_TYPE`; `_AuthorizationAppendCapability` (`__slots__=()`, identity-checked singleton `_AUTHORIZATION_APPEND_CAPABILITY`); guarded `append` → `_append_authorization` → shared `_append`.
- `executor.py` — capability import; issuance routed via `_append_authorization`; docstring documents provenance contract.
- `scientific_qc.py` — `_scientific_qc_verdict_schema()`; `validate_scientific_qc_verdict_payload()`; `_revalidate_verdict` delegation.
- `tests/integration/test_scientific_qc_gate.py` — §34: public append rejects exact forged event, `read_all() == ()`, file empty; then tampered-file reducer/replay `GraphEventContractError` "boundary_proof_digest". New tests: exact-copy attack (real issued event fields replayed through public `append` on same and fresh stores, both rejected before storage), capability identity attack (fake object / `copy.copy` / missing arg / wrong event type all rejected; public `append` of normal events unaffected; `hasattr` API assertions), schema-only negative payload (three-layer divergence proven, boundary rejects pre-write).
- `tests/contract/test_scientific_qc_verdict_contract.py` — production-validator contract: valid payload passes; negative payload rejected deterministically (`str(error)` equal across two calls); source-tree and packaged-layout resolution both return the repo schema and validate; both-missing → fail-closed.

## Commands And Observations

- New attack nodes (exact): `test_public_event_store_append_rejects_exact_authorization_event`, `test_specialized_authorization_append_requires_module_private_capability`, `test_boundary_rejects_payload_that_only_json_schema_catches` → **3 passed**.
- New contract suite: `uv run pytest tests/contract/test_scientific_qc_verdict_contract.py -q` → **4 passed**.
- Exact Task 3.7 suite: `uv run pytest tests/integration/test_scientific_qc_gate.py tests/graph/test_scientific_qc_isolated_veto.py tests/integration/test_no_draft_after_scientific_qc_rejection.py -q` → **16 passed**.
- Affected EventStore/executor/reducer/replay/graph suite: `uv run pytest tests/graph/ tests/integration/test_scientific_qc_gate.py tests/integration/test_no_draft_after_scientific_qc_rejection.py -q` → **29 passed**.
- Ruff: `uv run ruff check src tests` → `All checks passed!`
- Strict mypy: `uv run mypy src/ci_workflow/` → `Success: no issues found in 68 source files`.
- Schema/package: `uv run pytest tests/contract/test_package_manifest.py -q` → 1 passed; `uv run ci-workflow package verify --root .` → `PACKAGE_OK version=0.1.0a0 stage=phase-2-accepted`.
- `git diff --check` → clean (exit 0).
- Full suite: `uv run pytest -q` → **471 passed in 58.04s** (baseline 464; +7).

## Blockers Or Missing Environment

- None functional. Honest limit (documented in code): Python privacy is not hostile-process security — the contract is public-API provenance correctness, enforced at ingress + replay.
- [INFERENCE, tested]: current `uv_build` wheel does not bundle root-level `schemas/` (verified by building the wheel and inspecting entries); the packaged-layout schema branch is contract-tested via a simulated `site-packages` install tree, and a bare wheel install without the repo directory fails closed deterministically. The directory package remains the deployment contract (`package verify --root .`).

## Rerun Requests Or Next Step

- No rerun needed. Both false claims closed RED-first; exact 3+4 new, Task 3.7 16, affected 29, full 471; Ruff/mypy/package/diff clean. Codex and the isolated reviewer own final acceptance.
- Runner: persist this report to `runs/pi_ci_phase3_task37_third_fix_correctness_followup.md`. No commit made; not self-accepted.
