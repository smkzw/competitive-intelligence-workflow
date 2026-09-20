Re-reading only the cited changed files to verify each disposition.

Verifier line 715 still compares raw outcome — checking the cited decision docs and re-globbing the task dir before disposition.

All cited files re-read and cross-checked. Final follow-up report.

---

# Conference Participant Output: ci-phase9-task94-host-adapters - general_single_object (follow-up)

## (1) Former defect dispositions (A–F)

| # | Former finding | Disposition | Evidence |
|---|---|---|---|
| A | Runner/verifier rendered outcome mismatch | **Partially resolved; residual P2** | Runner now maps via `_EXPECTED_MANIFEST_OUTCOMES` (`rendered → completed`, unknown mapping fails closed) at host_smoke.py:84-88, 505-513, pinned by test_real_host_smoke.py:37-42. **Verifier at host_smoke.py:715 still compares raw `manifest.get("outcome") != expected_outcome` with no mapping** — see (2). |
| B | Dunder-interception boundary bypass | **Resolved** | `HOST_ADAPTER_FORBIDDEN_SPECIAL_METHODS` deny-list (base.py:489-500) enforced in `__init_subclass__` (base.py:524); counterexample tests for `__setattr__`/`__getattribute__` (test_base_adapter.py:82-87); ordinary private helpers still permitted. |
| C | Fresh-install layout undefined (wheel assumption) | **Resolved as non-defect — my assumption was wrong** | Phase 0 boundary (`.trellis/tasks/08-10-phase-0-foundation/implement.md:55`): "Python wheel 只承载 CLI 模块；Task 9.5 仍负责完整 `.tar.zst` Skill bundle、fresh install 和三真实宿主验收". Now codified in design.md:29, implement.md:13-17, authoritative-boundaries.md:9-14 (bundle must carry root package-manifest.json, unique fixture catalog, host-smoke-v1 inputs, schemas, console entry in repo-relative layout). |
| D | `semantic_receipt_digest` unverifiable | **Resolved as documented decision** | design.md:13 downgrades it to runtime diagnostic ("不单独充当事后真实性判据"), consistent with host_smoke.py:611-612. |
| E | `_manual_inbox_pending` hard-abort on malformed record | **Unchanged; P3 backlog** | base.py:307 still bare `ValueError`. Not raised as addressed; non-blocking. |
| F | `awaiting_user` hardcoded summary reason | **Unchanged; P3 backlog** | base.py:387. Non-blocking copy precision. |

## (2) Remaining P0/P1/P2 findings

**P0: none. P1: none.**

**P2 (one): verifier/runner outcome-vocabulary asymmetry persists** — `src/ci_workflow/application/host_smoke.py:715`:
```python
if manifest.get("outcome") != expected_outcome:
    raise HostSmokeReceiptError("宿主回执验证失败：manifest 结果与 catalog 预期不一致")
```
`expected_outcome` is raw catalog vocabulary (`"rendered"`) while a successful run's disk manifest says `"completed"` (confirmed via run_service/fixture_runner mapping and by the fix's own `_EXPECTED_MANIFEST_OUTCOMES`). The runner (fixed, line 505-513) would now happily produce a rendered receipt; the verifier would reject it at 715-716. Since Codex's decision explicitly keeps the official host-smoke fixture evidence-blocked ("successful report generation is not being redefined as the host-smoke fixture"), this path is **outside shipped scope and latent** — hence P2, not P1. It is a genuine internal contradiction between two halves of the same HA09 contract and the exact one-line remediation (`expected_manifest_outcome = _EXPECTED_MANIFEST_OUTCOMES.get(expected_outcome)` + use it at 715) was already validated by the runner fix.

## (3) Task 9.4 closability

**Closable, subject to Codex governance gates.** Specifically:
- No P0/P1 defect remains; the only P2 is latent and out of official scope.
- Remaining open gate is exactly the last unchecked item of implement.md:11 — independent conference review of the boundary/consistency/receipt-authenticity/Chinese-UX surfaces followed by the governance audit and close-out. This pass is that review; the governance close-out belongs to Codex.
- Codex's execution evidence (115 focused + 347 integration tests, Ruff, strict mypy, package verify, targeted diff check) is accepted as provided; I could not independently execute (Bash denied in this session) — that residual is Codex-side, not a Task 9.4 defect.
- Recommendation: either apply the one-line verifier alignment now (cheapest, removes the contradiction) or add an explicit "rendered receipts are outside the host-smoke contract" comment at host_smoke.py:715 so the asymmetry is a recorded decision, not a silent trap.

## (4) Task 9.5 carry-forward items (must NOT block Task 9.4 closure)

1. **Full `.tar.zst` Skill bundle fresh-install** in an isolated unpacked directory, producing three `path_resolved` host receipts for host-smoke-v1 (implement.md:16). Empirically unverified until then — the bundle layout contract is now documented (design.md:29) but no artifact exists yet.
2. **Bundle resource locatability**: root `package-manifest.json`, unique `fixtures/catalog.yaml`, `fixtures/synthetic/host-smoke-v1/`, packaged schemas, and console entry must resolve from the unpacked bundle (the repo-relative `parents[3]` resolution assumption must be proven in the bundle layout, not assumed).
3. **P2 recommendation** from (2): verifier alignment at host_smoke.py:715, or the explicit out-of-scope note, must be settled before any rendered-format host receipt is ever issued in Task 9.5.
4. **P3 backlog** (optional): Defect E (inbox hard-abort) and F (awaiting_user summary wording) — can be fixed in Task 9.5 without touching Task 9.4 evidence.

**Verdict: no P0/P1 remains; one latent P2 (host_smoke.py:715) + two P3 backlog items. Task 9.4 is closable after Codex rules on the P2 (one-line fix or documented scope note) and completes the implement.md:11 governance gate. I do not claim final acceptance — that is Codex's.**
