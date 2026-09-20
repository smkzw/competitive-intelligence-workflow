Final re-review. Confirming the exact current state of the cited regions.

Both cited regions confirmed at current workspace state. Final re-review follows.

---

# Conference Participant Output: ci-phase9-task94-host-adapters - general_single_object (final re-review)

## (1) Former P2: resolved

`verify_host_smoke_receipt()` now resolves the manifest vocabulary through the same shared mapping as the runner, and unsupported outcomes fail closed in both halves:

- Verifier R08 (host_smoke.py:684-685): `expected_manifest_outcome = _EXPECTED_MANIFEST_OUTCOMES.get(expected_outcome)`; `if expected_exit is None or expected_manifest_outcome is None: raise …catalog 预期结果不支持冒烟绑定`; comparison at host_smoke.py:716 uses `expected_manifest_outcome`.
- Runner (host_smoke.py:505-508): identical mapping + None fail-closed + comparison against mapped value.
- Mapping contract: `_EXPECTED_MANIFEST_OUTCOMES = {"evidence_blocked": "evidence_blocked", "rendered": "completed"}` (host_smoke.py:85-88), pinned by `test_fixture_outcomes_map_to_real_run_manifest_vocabulary` (test_real_host_smoke.py:37-42).
- Implementation record updated: implement.md:6 states "runner 与 verifier 均把案例 `rendered` 明确映射为运行清单 `completed`".

The runner/verifier asymmetry is gone; there is no code path where a produced receipt is rejected solely on outcome vocabulary. **Disposition: resolved.**

## (2) Remaining P0/P1/P2: none

No P0, P1, or P2 defect remains. Evidence for the no-defect conclusion:
- Outcome mapping symmetric across runner and verifier (host_smoke.py:505-513, 684-685, 716).
- Boundary hardening (base.py:489-500, 524) and counterexample tests (test_base_adapter.py:82-87) unchanged and present.
- Fresh-install boundary is a documented decision (design.md:29, implement.md:13-17, authoritative-boundaries.md:9-14, Phase 0 implement.md:55), not a defect.
- Live source-level smoke evidence recorded and honest (reviews/…/live_host_smoke_evidence.md; `real_host_pass=false` preserved).
- Codex-recorded verification after the change: 49 passed (real_host_smoke + receipt contract), Ruff passed, `git diff --check` passed (accepted as provided; I cannot execute in this session).

## (3) Closability

**Task 9.4 is closable, subject only to Codex governance gates** — no code defect blocks closure. The single remaining open implement.md item is line 11 (`[ ]` 独立会商审查…治理审计后收口): this final re-review completes the independent-review input; the remaining actions are Codex-side governance — run the conference/execution review-gates and `audit-execution --require-conference` per checkpoint.md:39,47, archive live-smoke receipt JSONs with the evidence, record `check.jsonl`/verification artifacts, then mark the Trellis task complete. I do not claim final acceptance.

## (4) Task 9.5 carry-forward items (not Task 9.4 defects)

1. Fresh-install the full `.tar.zst` Skill bundle in an isolated directory and produce three `path_resolved` host receipts passing batch verification (implement.md:16).
2. Prove bundle resource locatability: root `package-manifest.json`, unique `fixtures/catalog.yaml`, `host-smoke-v1` inputs, packaged schemas, and console entry must resolve from the unpacked bundle (the repo-relative `parents[3]` resolution must be demonstrated there).
3. Optional/recommended: if a rendered host-receipt path is ever introduced, add an end-to-end rendered smoke test (currently out of scope by decision; the vocabulary mapping is pinned as a dict contract only).
4. P3 backlog (optional): manual-inbox hard-abort on malformed record (base.py:307) and `awaiting_user` hardcoded summary reason (base.py:387).
