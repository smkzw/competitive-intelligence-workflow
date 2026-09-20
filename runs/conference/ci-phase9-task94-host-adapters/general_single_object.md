Trellis SessionStart ✓

Starting the independent review pass. Reading the initial read set first.

The conference context and plan are mostly templates with TODOs. The substance is Task 9.4 — I need to locate the actual task artifacts and the code under review.

Bash is unavailable; using Glob/Grep/Read instead.

Found Task 9.4 artifacts. Reading them all.

The hosts package exists. Reading all adapter sources now.

Now reading the test suite for hosts and the integration tests.

Reading the CLI and fixture runner to verify invocation-plan contracts and manifest formats.

CLI matches the invocation plan. Now the fixture runner to verify the manifest format used by receipt binding.

Let me check the run_service manifest format to validate the receipt binding logic.

One more contract check — whether `create_project_contract` enforces html-first ordering.

I have completed my independent review pass. All source and test files for Task 9.4 have been read; here is the complete report.

---

# Conference Participant Output: ci-phase9-task94-host-adapters - general_single_object

## Boundary Check

- **Read set honored**: read `context/ci-phase9-task94-host-adapters_conference_context.md`, `plans/codex_main_venue_ci-phase9-task94-host-adapters.md`, then the real substance under `.trellis/tasks/09-01-phase-9-task-94-host-adapters/` (task.json, prd.md, design.md, implement.md, research/authoritative-boundaries.md), plus the full Task 9.4 code surface: `src/ci_workflow/hosts/{base,codex,hermes,omp,receipt,__init__}.py`, `src/ci_workflow/application/{host_smoke,capability_preflight,fixture_runner,run_service}.py`, `cli.py`, `domain/contracts.py`, `storage/event_store.py`, `ingestion/manual_inbox.py`, `schemas/host-receipt.schema.json`, `fixtures/catalog.yaml` + `fixtures/synthetic/host-smoke-v1/`, `package-manifest.json`, `pyproject.toml`, and the full test set (`tests/hosts/*`, `tests/contract/test_host_boundary.py`, `test_host_receipt_contract.py`, `tests/integration/test_host_adapters.py`, `test_host_smoke_receipts.py`).
- **No other participant outputs were read** (no `reviews/` or `metrics/` files).
- **Hard boundary compliance**: no source edits, no production paths, no writer side effects. Bash was denied in this session, so **I could not execute pytest/ruff/mypy or run the real host smoke**; all "tests pass" statements below are read-only inferences, not executed evidence. This is explicitly listed under Verification Needs.
- **No final acceptance claimed** — Codex owns Task 9.4/9.5 closure.

## Independent Work Product

### Scope assessed vs. PRD acceptance criteria (1–8)

| Criterion | Verdict | Evidence |
|---|---|---|
| 1. Base class thin boundary | **Mostly sound, one structural bypass** | `base.py:503-534` `__init_subclass__` blocks shared-surface override, forbidden ops, extra public members, `__init__` override, illegal host names; AST import whitelist test. **Gap: all dunder/private members are exempt (`if name.startswith("_"): continue`)** — see Defect B. |
| 2. Three adapters same semantic state on same fixture | **Covered** | `tests/hosts/test_conformance.py` + `tests/integration/test_host_adapters.py`: receipts are pydantic-equal, serialized JSON contains no host label; failure classification, recovery requeue nodes, inbox/partial delivery all equal across hosts. |
| 3. Host-specific fields never affect scientific truth | **Covered at import/member level** | `test_host_layer_cannot_import_scientific_truth_layers` (AST), forbidden-op names with §6.3 message. **Gap: probe interception via `__setattr__` bypasses capability gating** — see Defect B. |
| 4. Selective capability blocking; HTML not blocked by PDF/PPTX/Office | **Covered** | `test_missing_delivery_components_do_not_block_first_version_html`, `capability_preflight.py` `_delivery_dependencies`. |
| 5. Environment recovery only requeues failed capability + downstream; inbox/partial equivalence | **Covered** | `plan_environment_recovery` (capability_preflight.py:600-659), HA07 tests incl. cross-host comparison rejection. |
| 6. `host-receipt` binds package/fixture/real entry/executable/session/run/events/manifest; same-process forgery, old receipt, adapter-only JSON fail closed | **Covered, strong** | `receipt.py` self-digest + `HostReceipt.model_validate` re-check; `verify_host_smoke_receipt` R01–R09; batch cross-host distinctness; tamper counterexample suite. **Residual weakness: `semantic_receipt_digest` never verified** — see Defect D. |
| 7. `host-smoke-v1` registered in unique catalog with per-file + case digest | **Covered** | `catalog.yaml:113-129`, `test_host_smoke_case_registered_with_file_and_case_digests`. |
| 8. Source-level + external-entry contract passes; Task 9.5 re-runs same contract after fresh install | **Source-level covered; fresh-install path unresolved** | Real-entry smoke runs via `resolve_real_entry` + external subprocess with explicit host doubles; `real_host_pass` correctly False. **Fresh-install resolution of catalog/package-manifest is undefined and likely broken for a wheel** — see Defect C. |

### Highest-impact defects found

**Defect A (high, latent) — `run_host_smoke` rendered path is dead code that would hard-fail.** `host_smoke.py:501` compares `manifest.get("outcome") != expected_outcome` where `expected_outcome` is the catalog's vocabulary (`"rendered"`) but the manifest outcome for a successful run is `"completed"` (confirmed in `run_service.py` — `_finalize("completed")` for rendered paths; `fixture_runner.py:416-418` maps `rendered → "completed"` for comparison). Therefore any rendered host-smoke case would raise `HostSmokeError("真实入口结果与预期不符")` at host_smoke.py:502. The complete/rendered receipt path is unit-tested **only** via synthetic `_build_receipt(RUN_COMPLETE)` — never through the real-entry runner. Consequence: the "交付成功" host-smoke path (exit 0, rendered receipt, artifact binding via the fragile `_run_evidence` string parsing at host_smoke.py:382-397) is unexercised end-to-end and would break Task 9.5 the moment a rendered smoke case is added. Since Task 9.4's only smoke case is `evidence_blocked`, current tests cannot catch this.
*Remediation*: normalize the comparison to the same mapping `fixture_runner` uses (`completed` for `rendered`), and add a rendered host-smoke test (e.g., parameterize or add a `host-smoke-v1-rendered`-style case reusing `a-complete`) that asserts a `state="complete"`, `outcome="rendered"` receipt with bound artifacts through the external-process path.

**Defect B (medium) — boundary enforcement is bypassable via attribute-interception dunders.** `base.py:508` `if name.startswith("_"): continue` exempts every private/dunder member, including `__setattr__`, `__getattribute__`, `__getattr__`, `__delattr__`. Because `HostAdapter.__init__` assigns `self.probe = probe`, and instance-attribute assignment is routed through the *subclass's* `__setattr__`, a malicious/errant future adapter can:
```python
def __setattr__(self, name, value):
    if name == "probe":
        value = AlwaysReadyProbe()      # or silently skip assignment
    super().__setattr__(name, value)
```
which corrupts capability gating → capability-blocked states, user messages, and (via `build_semantic_receipt`) the semantic receipt and the `semantic_receipt_digest` bound into host receipts — directly violating acceptance 3 and the "基类只允许…" structural contract that `test_private_host_helpers_are_still_allowed` celebrates. The test suite's freeze check (`dir(HostAdapter)`/`vars(cls)`) does not cover dunders.
*Remediation*: in `__init_subclass__`, explicitly reject attribute/behavior interception dunders (`__setattr__`, `__getattribute__`, `__getattr__`, `__delattr__`, `__reduce__*`, `__getstate__/__setstate__`) — or adopt a metaclass that freezes the subclass namespace. Private *data* members (the current allowed case) can remain allowed.

**Defect C (medium, Task 9.5 boundary) — fresh-install resource resolution is undefined and wheel-install likely broken.** In a wheel install, `host_smoke.py:_ROOT = parents[3]` resolves to site-packages, where neither `fixtures/catalog.yaml` (default catalog, host_smoke.py:74) nor `package-manifest.json` (host_smoke.py:80-83) exist — `_installed_package_identity` would fail closed ("安装包内找不到 package-manifest.json"), and the smoke default catalog would fail. `fixtures/` is not listed in `package-manifest.json` components, and `package-manifest.json` itself is only at repo root, not inside the `ci_workflow` package dir. So the "Task 9.5 fresh-install 复验用同一合同" promise (PRD 8, design.md「真实入口边界」) only holds if the candidate package is installed as a repo-root copy (path/editable install), which is never stated.
*Remediation / decision needed*: Codex must define the candidate-package install layout for Task 9.5 (wheel-with-bundled-fixtures-and-manifest vs. repo-directory install), and a contract test must assert the packaged layout resolves `fixtures/catalog.yaml` + `package-manifest.json` from the installed location. This is the exact "源码级验证与 Task 9.5 最终安装验收的边界" the conference objective asks to challenge.

**Defect D (low-medium) — `semantic_receipt_digest` is self-asserted, unverifiable, and decoration-only in the verification path.** `host_smoke.py:603` documents that the validator never recomputes it ("运行时点稳定"); therefore any 64-hex string passes R01–R09. The design.md claim that the receipt "绑定…语义回执" is structurally weaker than it reads. Impact is bounded (state/no-draft/artifacts are cross-checked against manifest + disk), but the field adds forgery surface without verification.
*Remediation options*: (a) downgrade the claim in design.md to "运行点证据，不参与验证"; or (b) make verification recompute it deterministically where possible (it is deterministic *given* a probe snapshot — the flakiness is the runtime probe; a StaticCapabilityProbe-based recompute would only work in tests).

**Defect E (low) — `_manual_inbox_pending` hard-aborts on any malformed record** (`base.py:306-307` raises bare `ValueError`), which fails *all three* hosts' semantic receipts on one corrupt/legacy jsonl line, and the error is not a typed contract error. Consider skip-and-surface with a typed diagnostic, or schema-validate at write time.

**Defect F (low, copy) — `awaiting_user` summary reason is hardcoded** ("自动检索穷尽后仍有少量关键原文无法公开获取。" base.py:387), which can mis-describe login-required cases (登录资料浏览器). The per-item reason is precise; derive the summary from pending item reasons instead of a fixed sentence.

### Verified sound (positive findings)
- `_parse_outputs` (contracts.py) always forces html-first → `MinimalUserInput` html-first validator is consistent with all real projects.
- Invocation-plan command strings match the real CLI (`cli.py`: `project create --root/--indication/--reports/--outputs`, `capability preflight --host/--project`, `project run --root [--resume]`), verified against parser definitions.
- Receipt self-digest algorithm is identical across the pydantic and dict paths (`receipt_digest` test pins it); `model_validate` rejects digest drift; two schema copies byte-identical and registered in package-manifest.
- Batch honesty: `real_host_pass` requires all three `path_resolved`; explicit doubles and unavailable hosts cannot claim pass; `host_unavailable` receipts still bind real run evidence.
- CLI/host semantics share one `run_capability_preflight`; `capability preflight --host X` test compares adapter vs CLI matrices excluding `host`.
- Chinese user surface: all status/reason/action/inbox strings are native Chinese; backend state words are not leaked into user-facing fields; only proper nouns (ClinicalTrials.gov, PPTX/PPT Master/HTML/PDF) appear.

## Evidence And Assumptions

- Evidence: file contents as read (all cited paths/line numbers above are exact).
- Assumption: pydantic v2 semantics as documented; `EventStore.read_all()` returns append-ordered events (confirmed); manifest `outputs` entries carry `relative_path`/`sha256` (confirmed in `run_service._output_file_dict`); `run_project` outcome vocabulary is `completed/running/evidence_blocked/failed/renderer_unavailable` (confirmed).
- Inference: Defect A is real only if a rendered case ever flows through `run_host_smoke`; currently masked by the evidence-blocked-only catalog. Defect C is a blocking risk only if Task 9.5 uses a wheel-style install.
- Uncertainty: I could not run pytest/ruff/mypy, the real-entry smoke, or check PATH presence of `codex`/`hermes`/`omp` on this machine (Bash denied). All "covered" verdicts are test-code-level claims, not executed green runs.

## Risks, Gaps, And Verification Needs

1. **Execute the Task 9.4 suite** (pytest `tests/hosts tests/contract/test_host_boundary.py tests/contract/test_host_receipt_contract.py tests/integration/test_host_adapters.py tests/integration/test_host_smoke_receipts.py`) plus ruff/mypy/package-verify, and record results in `check.jsonl`. Without a green run, Task 9.4 cannot be closed regardless of code quality.
2. **Fix or explicitly scope Defect A** before close — a rendered host-smoke case is the natural Task 9.5 acceptance vehicle; the broken comparison will surface there.
3. **Decide Defect C**: define the candidate-package install layout now (it is a Task 9.4 design decision, not a Task 9.5 discovery) and add a layout contract test.
4. **Harden Defect B** with a denial-list of interception dunders + a counterexample test (currently no test covers dunder-based overreach).
5. Optionally record Defects D/E/F as Task 9.5 backlog or fix in-place (all three are cheap).

## Recommended Next Step

Codex should: (1) run the full Task 9.4 verification gates and record results; (2) rule on Defects A and C (fix-in-place vs. Task 9.5 scope); (3) harden Defect B; then either dispatch a bounded same-session follow-up to me for re-review of the changed files or close the conference with the recorded decisions. **My verdict: Task 9.4 is not closable as-is** — it is high-quality WIP, but the rendered host-smoke path is unexercised/broken, the boundary contract has a dunder bypass, the fresh-install layout is undefined, and no executed test evidence exists yet. None of these require re-planning; all are bounded fixes or explicit scope decisions.

**Questions for Codex (precise, bounded):**
1. Should the rendered host-smoke path (Defect A) be fixed and tested in Task 9.4, or is the evidence-blocked-only smoke a deliberate Task 9.4 scope and the fix deferred to Task 9.5? If the latter, I recommend adding a one-line "已知限制" entry to implement.md so the Task 9.5 acceptance criteria can name it.
2. What is the Task 9.5 candidate-package install layout (Defect C) — wheel with bundled `fixtures/` + `package-manifest.json`, or repo-directory install? The `package_digest` binding and default catalog resolution both depend on this answer.
3. Is the dunder-interception bypass (Defect B) in scope for Task 9.4 hardening, or accepted as a documented residual risk?
