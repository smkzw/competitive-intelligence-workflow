Trellis SessionStart ✓

Bounded conference worker: independent, read-only R2 acceptance challenge. Reading the initial read set now.

Now reading the source implementation files.

Reading the remainder of run_service.py and then the tests.

Now reading the test files.

Now let me examine supporting modules: the host receipt types, visual acceptance gating, and how report states flow.

Let me check the gate script and the A/C real acceptance tests.

Let me inspect the test helper that fabricates the verified scientific review, to understand what the positive-path tests simulate.

Let me verify the pytest marker/scope configuration and marker distribution.

Let me check the layering audit's blind spot for alternate import syntaxes and the A-path report_states question.

Let me verify how report_states are recorded in the A fresh-source path and the legacy `snapshot_locked` writers.

I have completed a full independent read-only audit of the read set (canonical contracts, execution plan, checkpoint, review, the six source modules, and all listed tests, plus gate/layering configuration). Below is the complete conference output.

---

# Conference Participant Output: ci-r2-review-runtime-fixture-acceptance-20260905 - general_single_object

## Boundary Check

- Working directory: `competitive-intelligence-workflow` only. Read-only; no file edits, no commands that mutate state, no network research, no reads of the former Chinese-named workspace, no credentials/browser sessions touched.
- Evidence used is limited to the initial read set plus direct verification reads inside the workspace (`tools/gate.sh`, `pyproject.toml`, `src/ci_workflow/hosts/receipt.py`, `src/ci_workflow/application/visual_acceptance.py`, `src/ci_workflow/capabilities/scientific_qc.py`, marker/import greps across `tests/` and `src/`). No worker reports beyond the named Codex review were consulted.
- No R2, RC, release, clinical, or visual acceptance is claimed anywhere in this output. This is an adversarial challenge report only.
- Runner-managed report path was not written; the complete schema is returned inline.

## Independent Work Product

### Stage verdict (per assigned question)

**Q1 — Can spoofed receipt/verdict, cross-project/snapshot/run replay, self-review, same-session review, stale content, time rewrite, missing lineage, or artifact byte drift still promote B/C?**

Verdict per vector (evidence-based):

| Vector | Status |
|---|---|
| Structurally spoofed receipt/verdict JSON (wrong shape, forged `verified` status, digest drift, non-verdict artifact, hand-edited file) | **Rejected.** Schema (Draft 2020-12) + pydantic semantic validators (`qc/review_receipt.py:436-454`, `:254-292`), receipt self-digest re-verification (`:300-306`), artifact byte re-hash (`:368-375`), verdict re-validation and 16-point binding agreement (`scientific_review_transition.py:436-504`). Negative tests cover each (`tests/integration/test_scientific_review_transition.py:482-583`). |
| Cross-project replay | **Rejected.** `project_id` + `context_digest` + report-kind-scoped receipt paths bind to a single project/candidate; copied receipts fail binding (`review_receipt.py:378-409`; `scientific_review_transition.py:489-493`). |
| Cross-snapshot / cross-candidate replay | **Rejected.** `candidate_snapshot_id`, `candidate_content_digest`, `gate_result_key`, `criteria_version`, coverage ids/digest all must equal the context rebuilt from the current package bytes (`review_receipt.py:389-405`; `scientific_review_transition.py:463-488`). |
| Cross-run replay | **Blocked for acceptance**, permitted idempotently for promotion. The production review request preserves the first production identity for the same candidate (`scientific_review_transition.py:312-327`); re-promotion on a later resume of the same candidate is harmless and byte-stable because the format node is reused. |
| Self-review / same-session review | **Rejected** (`review_receipt.py:278-283`); covered by tests (`test_scientific_review_transition.py:521-536`). |
| Stale content | **Rejected.** Content digest must equal current candidate digest; old-context receipt vs current context fails (`review_receipt.py:284-285` + bindings; test `:539-551`). |
| Time rewrite | **Partially closed, residual risk.** Internal ordering enforced (`produced_at < started_at <= finished_at <= issued_at`; verdict `reviewed_at` inside process window; `valid_until > issued_at`) — `review_receipt.py:286-289`, `scientific_review_transition.py:496-503`. **Not enforced:** `issued_at <= now` at promotion (a future-dated or long-expired receipt validates); `valid_until` is not checked against promotion time (only vs issuance) (`scientific_review_transition.py:502-503`). All timestamps are self-declared; consistent timestamp rewriting is undetectable without an OS/attestation anchor. |
| Missing lineage | **Rejected.** `derive_scientific_source_refs` requires persisted fact-version mapping and claim lineage per source (`scientific_review_transition.py:127-198`); empty refs fail model validation (`qc/scientific.py:459-477`). |
| Artifact byte drift | **Rejected** at receipt gate and at acceptance (receipt artifact bytes `review_receipt.py:368-375`; site directory digest `real_source_acceptance.py:367-397`; run-manifest output tuple incl. exact `mtime_ns` `run_service.py:969-1099`). |
| **Forgery with full project write access (recomputed digests)** | **Not prevented.** All protections are self-digests inside the trusted project directory; an actor who can write the project and recompute SHA-256s can fabricate a structurally perfect receipt+verdict pair. Nothing cryptographically or OS-level binds the claimed reviewer process (PID/argv/session) to reality. |

**Q2 — Does the review request bind the original production run/session and immutable review input strongly enough, and does resume preserve rather than rewrite it?**

Mostly yes, with two caveats:
- Strong binding: `producer_session_id` = the producing run id is materialized into `ReviewProductionContext` in the review request (`run_service.py:1677-1684` + `scientific_review_transition.py:293-306`); the receipt must equal the stored request byte-for-byte (`scientific_review_transition.py:527-533`); resume with the same candidate reuses the original request (first-production identity preserved, `:312-327`); a changed candidate changes `context_digest` and the stale request/receipt fails closed.
- Caveat 1 (P2): promotion is not conditioned on a *completed render of the candidate existing before review eligibility*. In `run_service.py`, the receipt check/promotion executes at `:1686-1730`, i.e. **before** the `analyze`/`format` nodes (`:1731-1774`). A resume whose event history lacks a completed `format:{kind}` node (e.g., first run crashed between renderer write and node completion, or a receipt file was placed before any render) promotes the candidate and then *renders fresh HTML in the same run*, recording `scientifically_reviewed_rendered_candidate` while violating "promotion reuses immutable bytes". Final real-source acceptance catches it (`real_source_acceptance.py:245-265` requires `format:{report} == reused`), but visual acceptance would not, so release integrity depends on always running real-source acceptance.
- Caveat 2 (P3): the reviewer-facing production request is published before the first run renders (`:1677-1684` precedes `:1745-1774`), so the review bundle cannot contain the rendered artifact digest; reviewers certify the *content digest*, and byte certification is deferred to manifest/snapshot/reuse checks. This is coherent but should be stated as a deliberate two-plane design (content review vs. byte acceptance).

**Q3 — Does promotion reuse the exact HTML bytes, and does real-source acceptance validate the controlled two-run chain without accepting arbitrary reused artifacts?**

- Promotion itself reuses bytes only *indirectly*: it does not copy or rewrite the site; byte-identity is preserved because the `format` node is reused on identical input digest and the run manifest records `reused_artifacts` with sha/size/mtime (`run_service.py:1184-1236`, `:2707-2753`, `:1033-1046`). The html.manifest.json is the byte anchor (site dir digest inside it), re-verified at acceptance (`real_source_acceptance.py:367-397`).
- The two-run chain is genuinely controlled: promotion requires `resume`, exactly one accepted report, `scientific_qc:{report} == completed`, `format:{report} == reused` exactly once with a run id different from the current one, non-empty `reused_artifacts`, and the entire event chain restricted to exactly {producer run, resume run} (`real_source_acceptance.py:236-290`). Arbitrary reuse from third runs or unrelated history fails closed; stale mtimes fail closed (`:185-189`, `:370-397`).
- Residual (P3): acceptance freshness is anchored to the recorded run start, not to acceptance execution time; a structurally valid project whose runs happened earlier is re-acceptable if source/package digests still match (no `expected_run_id` bound in the positive real tests, `tests/acceptance/test_report_b_real.py:36-43`; parameter is optional at `real_source_acceptance.py:781`). Directory copy replay of an accepted project is not detected by the acceptance code. Mitigation is procedural (fresh release root + bound `expected_run_id` per R6 project).

**Q4 — Can a report-data preview, missing declared snapshot, or synthetic fixture be mistaken for real-source/scientific/visual/RC acceptance?**

- Report-data preview: cannot reach acceptance. All report-data/fixture paths record `rendered_unreviewed` and are rejected by `require_accepted_origin_report_states` at both acceptance roots (`run_service.py:2104/2235/2269/2298`; `acceptance_boundary.py:13-38`; consumers `visual_acceptance.py:442-446`, `real_source_acceptance.py:408-412`). Promotion logic exists only in the B/C fresh research-package branch, so a plain report-data project can never become reviewed even with a receipt file present.
- Missing declared snapshot: not trusted — self-locks from actual data and stays `rendered_unreviewed`; corrupt/unbound declared snapshots fail the run closed (`tests/acceptance/test_preview_report_snapshot_contract.py:101-129, 243-279`).
- Synthetic fixture as real acceptance: a fixture run is rejected by `case_id/case_digest` (`real_source_acceptance.py:221-222`). **However**, the synthetic-project tests in `tests/acceptance/test_report_a_real.py:141-325` build a C project with fixture research content, fabricate a verified receipt via the test helper, and fabricate a *structurally complete synthetic browser verdict* (fake PNGs, ZIP traces), and `verify_current_run_exact` accepts it (`:309-325`). This is intentional (negative-test scaffolding), but it proves the acceptance machine is content-agnostic: it validates run/byte/browser-report structure, not scientific realness. Real-source "realness" lives upstream (research/package formation + scientific review), and the positive real tests skip when the external acceptance root is absent (`test_report_a_real.py:328-332`, `test_report_b_real.py:25-29`).
- Visual acceptance (`accept_visual_artifact`, B-only) certifies from self-declared plan/render-evidence/verdict JSONs and never opens the declared screenshot files — the test suite itself fabricates those JSONs without creating PNGs and passes (`tests/acceptance/test_visual_acceptance.py:57-86, 205-224, 313-350`). The screenshot/trace/PNG/mtime checks exist only in the real-source acceptance path (`real_source_acceptance.py:511-545, 666-727`). So visual acceptance alone would accept fabricated evidence; release integrity depends on the full-matrix real acceptance always running.

**Q5 — Does the HTML-only test layer retain basic non-HTML regressions while keeping them outside v1 release semantics, without hiding full-tree debt?**

- Layering contract is explicit and enforced for declarations: 18 retained files, module markers, marker registration, legacy-root closure, active-layer import audit (`tests/contract/test_v1_test_layering.py:69-114`). The gate reports its real scope and does not count the retained layer as v1 acceptance (`tools/gate.sh:87, 100-101`).
- Gap found (P2): `tools/gate.sh` executes pytest **only on `tests/unit tests/contract`** (`:100-101`). Of the 18 declared retained files, only 2 live under that scope (`tests/contract/test_ppt_master_job.py`, `test_ppt_master_job_contract_vectors.py`); the other 16 (all of `tests/pdf`, `tests/html_ppt`, plus retained files under `tests/acceptance`, `tests/graph`, `tests/renderers`) are validated only by declaration/marker audit and are **never executed by the gate**. The checkpoint's "retained legacy `20 passed`" therefore reflects only the PPT-master contract files; the actual PDF/HTML-PPT/PPTX renderer regressions are retained in name, not run by the single quality gate. The gate's scope print is honest, but the checkpoint phrasing ("gate reports both layers… retained legacy 20 passed") overstates what runs.
- No hidden debt found in the import audit itself: only declared legacy-root files import legacy runtimes today, and the four-signature audit also catches submodule `from ci_workflow.renderers.html_ppt.projections…` forms via `\b`. A residual hole exists for the rewritten form `from ci_workflow.renderers import pdf_native` (audit regex misses it), but no current file exploits it.

**Q6 — R2 now vs. R3/R4/R5 vs. YAGNI rejections** — see finding dispositions below.

### P0–P3 findings

**P0 — none found.** No ordinary-operation path, replay, spoof, preview, or fixture path bypasses the final acceptance gates as currently wired and gated by the R6 flow.

**P1-01 — Scientific-review receipts have no production issuance path; "independent review" is only as strong as host discipline and is today simulated everywhere.**
- Location: `src/ci_workflow/qc/review_receipt.py:309-347` (`build_scientific_review_receipt`); only importers are tests (`tests/integration/test_scientific_review_transition.py:52,287`, `tests/unit/reports/b/test_fresh_b_research_package.py:1040,1108`, `tests/contract/test_scientific_review_receipt_contract.py:37`). No CLI, skill, or application entry point issues a receipt from *captured* host process/session evidence; `capabilities/scientific_qc.py:483` is an unrelated graph event-store authorization.
- Impact: the R2.4 exit criterion "real independent-host receipt against a current B/C candidate" (checkpoint line 55-57) has no productized mechanism — a reviewer host would have to hand-write receipt+verdict JSON against the schema, or ad-hoc import the builder. Test green-lines for promotion all fabricate process evidence with hard-coded PIDs/argv (e.g., `tests/integration/test_scientific_review_transition.py:239-259`), so the runtime cannot currently distinguish a genuinely issued receipt from a producer-fabricated one with recomputed digests. This is the single largest residual trust gap in the R2 review boundary and confirms Q1's "forgery with write access" vector.
- Smallest remediation: (a) add a minimal receipt-issuing CLI (e.g., `ci-workflow review-issue --request state/scientific_review/{kind}/review_request.json --verdict …`) that validates the request, launches/captures the external reviewer evidence, and writes the receipt+digest, plus a documented two-command reviewer checklist; or (b) explicitly record in `design.md`/roadmap that receipt independence is a host-process-discipline trust root with no in-repo forgery defense, and make R2.4's real issuance exercise follow a repeatable recorded procedure. Option (a) is preferred; (b) is the minimum.
- Changes: design/roadmap note (trust root), R2.4 must-fix.

**P2-02 — Promotion can certify a candidate whose rendered HTML was never previously completed/reused (promotion precedes the format node and ignores render history).**
- Location: `src/ci_workflow/application/run_service.py:1686-1730` (promotion before `format` at `:1745-1774`); `promote_rendered_candidate` (`scientific_review_transition.py:507-539`) has no event-history precondition.
- Impact: on a resume where the first run ended between renderer write and node completion (or a receipt pre-placed before any render), the run records `scientifically_reviewed_rendered_candidate` while the HTML is freshly produced in the same run — contradicting the "reuse immutable bytes" contract at the runtime layer. Final real-source acceptance rejects it (format must be `reused`), and C's renderer refuses to overwrite an existing version dir (`run_service.py:660-661`), so release integrity holds — but only if real-source acceptance always runs; visual acceptance alone (`visual_acceptance.py:442-446` checks state only) would accept.
- Smallest remediation: before promoting, require a completed `format:{kind}` node with the current input digest in the event history (or require the current run's manifest to record `format:{kind} == reused`); add a negative test "valid receipt + no prior completed format node → promotion refused".
- Changes: code + test; no design change.

**P2-03 — Fresh A research-package runs never record `report_states`, so A cannot pass real-source acceptance; A also lacks the B/C two-stage chain.**
- Location: `src/ci_workflow/application/run_service.py:1801-1996` (fresh-A path ends at `:1996` with no `runtime_metadata["report_states"]` — contrast B/C at `:1786-1798`, report-data paths at `:2102-2111/2233-2240/2266-2272/2296-2303`); consumers require it (`real_source_acceptance.py:408-412`; `acceptance_boundary.py:25-38`); A's `scientific_qc` node is fed from the package's own embedded `scientific_review` (`run_service.py:1929-1943`).
- Impact: the current R6 gate for A portals is structurally unpassable (no accepted origin state exists in fresh-A run manifests), and A's "independent review" remains producer-supplied inside the research package with no host receipt boundary, unlike B/C. Old Task 10.2 A evidence passed under the superseded machinery; the checkpoint attributes their current failure only to package digest, but even a digest-current A project would now fail on `report_states`.
- Smallest remediation (decision needed): either wire A into the same two-stage receipt chain (extend `scientific_review_transition` to A) or explicitly define A's package-embedded review as the v1 A contract and record a derived accepted state in the fresh-A run manifest; add a test `verify_current_run_exact` against a current fresh-A project.
- Changes: design/roadmap amendment (A review contract + state wiring); fix before R6 A matrix; not an R2-blocking defect for the B/C slice but the boundary module is shared, so record the decision in R2.4.

**P2-04 — Visual acceptance certifies from self-declared JSON and never verifies declared screenshot bytes exist.**
- Location: `src/ci_workflow/application/visual_acceptance.py:402-501` (plan/evidence/verdict digest bindings only); screenshot file checks exist only in the real acceptance path (`real_source_acceptance.py:669-687`). Tests exploit this by fabricating evidence without PNGs (`tests/acceptance/test_visual_acceptance.py:57-86, 205-224, 313-350`).
- Impact: `accept-visual` alone would accept hand-authored evidence; the product's intended defense is real-source acceptance and R6 ordering. For a B report that was promoted but never real-source-accepted, delivery_ready is reachable with fabricated visual evidence.
- Smallest remediation: in `accept_visual_artifact`, verify each declared screenshot exists, is a PNG, and has mtime ≥ candidate artifact modified_at (same predicates as `real_source_acceptance._png_is_real`/`_not_older_than`); update the test to write real PNGs.
- Changes: code + test; deferrable to R4.5/R5 but cheap enough to schedule near R2.4.

**P2-05 — The gate does not execute most of the declared retained non-HTML regression files.**
- Location: `tools/gate.sh:100-101` (scope `tests/unit tests/contract`); 16 of 18 retained files live outside that scope (`tests/contract/test_v1_test_layering.py:43-62` vs. file locations).
- Impact: PDF/HTML-PPT/PPTX renderer regressions are declared and marker-audited but are not run by the single quality gate; the checkpoint's "retained legacy 20 passed" count cannot cover them. This understates full-tree regression coverage and can let retained-format code rot without the gate noticing.
- Smallest remediation: either extend the retained step to the exact `RETAINED_FILES` list (running what is runnable without browser/poppler infra) with an explicit not-run list, or tighten `test_v1_test_layering` to assert every retained file is covered by a documented runnable command and record which are not executed in the gate output.
- Changes: gate/layering contract; R2.4-adjacent (debt-visibility), not release-blocking.

**P3-06 — `valid_until` is not enforced at promotion time; future-dated receipts accepted.**
- Location: `src/ci_workflow/application/scientific_review_transition.py:502-503` (only `valid_until <= issued_at` is checked).
- Remediation: enforce `receipt.issued_at <= now` and treat an expired `valid_until` at promotion as a fresh-review requirement (or drop the field and document that criteria/content digests are the freshness anchors).
- No design/roadmap change; small code+test.

**P3-07 — Trust root is undocumented: all digests are recomputable inside the project directory.**
- Location: whole receipt/promotion chain; e.g., `review_receipt.py:290-307`, request digest at `scientific_review_transition.py:324`.
- Remediation: one explicit paragraph in `design.md` §5.4/§13 stating the v1 trust model (project directory + host process separation are trusted; digests stop accidental drift/blind copy, not a motivated forger), and that R2.4 real issuance exercises the discipline.
- Changes: design note only.

**P3-08 — Real-source acceptance does not bind `expected_run_id` in positive tests and does not detect directory-copy replay.**
- Location: `tests/acceptance/test_report_b_real.py:36-43` (no `expected_run_id`); `real_source_acceptance.py:781` (optional).
- Remediation: bind `expected_run_id` in the R6 acceptance checklist; optionally record project-root birth/inode evidence.
- Changes: roadmap/R6 acceptance note.

### Proposed adoption decisions (采纳 / 修改后采纳 / 延后 / 拒绝)

- P1-01 receipt issuance path: **采纳（修改后采纳，取选项 (a) 最小 CLI + 文档流程）** — must close inside R2.4; the R2 milestone exit evidence depends on it.
- P2-02 promotion-before-format guard: **采纳** — small code+test change in R2.4.
- P2-03 A report-state wiring / A review contract decision: **采纳（决策记录 + 状态接线）** — decision now, fix before R6 A matrix; do not leave `snapshot_locked` as an unreachable phantom state for A.
- P2-04 visual-acceptance screenshot verification: **修改后采纳 / 可延后至 R4.5** — improvement is small; if scheduled late, the R6 real acceptance ordering must remain the documented acceptance root.
- P2-05 retained regression execution scope: **修改后采纳** — extend gate retained step or explicitly declare non-executed files; must not silently inflate "retained" claims.
- P3-06 `valid_until`/future-dated receipts: **采纳**（小修复）。
- P3-07 trust-root documentation: **采纳**（文档）。
- P3-08 `expected_run_id` binding: **采纳于 R6 清单**, not in code now.
- Proposed enhancements to reject under YAGNI: OS-level process attestation / PID liveness verification at promotion, external signing keys, receipt nonce registries, per-portal visual re-verification tooling, moving receipts to an external store — all out of v1 contract and unnecessary given the declared trust model; record as rejected in the disposition.

### Design/roadmap/plan amendments

1. `design.md` §5.4/§13: add explicit trust-root statement (P3-07) and the "content review vs. byte acceptance" two-plane note (Q2 caveat 2).
2. Roadmap R2.4 exit evidence: add "receipt-issuing CLI or documented recorded issuance procedure exercised against a current B/C candidate" as an explicit deliverable (P1-01); add A review-contract decision item (P2-03).
3. Execution plan: extend `tools/gate.sh` retained step or layer audit to cover all 18 retained files (P2-05); record R6 acceptance items with `expected_run_id` binding (P3-08).

## Evidence And Assumptions

- Evidence: all cited `file:line` above were read directly in this session (source, tests, gate, pyproject, receipts schema location, marker distribution).
- Assumptions: (1) the R6 flow always invokes `verify_current_run_exact` per portal before any release signal — this is what the roadmap/plan state, and findings P2-02/P2-04 rely on it; (2) the "independent reviewer" is a genuinely separate host session per the checkpoint's R2.4 remaining item; (3) tests/integration and tests/acceptance are not part of `tools/gate.sh` by design (scope is printed in `GATE_SCOPE`).
- The checkpoint's gate numbers (`904 passed/20 deselected`, `20 passed/904 deselected`) could not be reconciled by static reading (only 2 retained files exist under the gate's `tests/unit tests/contract` scope; the reported numbers imply 20 marked items there). The retained run's "20 passed" likely equals the test count of those two PPT-master contract files — listed as unverified; I did not execute the gate (read-only pass).

## Risks, Gaps, And Verification Needs

- Highest-impact defect surfaced: **the entire B/C "independent review" chain currently has no production issuer and every positive promotion test fabricates its receipt** (P1-01). Until R2.4 exercises a real issuance, promotion green-lines prove the validator, not the independence claim.
- Second: **promotion-before-format** (P2-02) and **A's missing report-state wiring** (P2-03) are latent acceptance-path gaps that only final-matrix ordering currently masks.
- Verification needed by Codex: reproduce P2-02 with a negative test (receipt valid + no completed format node in history); confirm whether fresh-A runs record report_states anywhere not visible to me; confirm the actual gate invocation/counts behind the checkpoint; decide the A review contract; decide issuance mechanism for R2.4.
- If a decision or input blocks a conclusion, state: my conclusions hold for the code as read; items requiring live runs (real receipt issuance, real browser verdicts, real 24-portal matrix) are outside a read-only pass and remain open regardless of my findings.

## Recommended Next Step

**有条件继续** — the bounded R2 slice is structurally sound and fail-closed at the acceptance layer, but R2 cannot be declared complete and R2.4 must close P1-01, P2-02, and record the P2-03 A decision before the real issuance exercise; RC/visual/release acceptance is not claimed.

Next steps (3–7):
1. Codex reopens and reproduces P2-02 (promotion without prior completed format node) with a deterministic negative test.
2. Decide and implement P1-01: minimal receipt-issuing CLI (or recorded manual issuance procedure) and exercise it in the R2.4 real independent-host run against a current B/C candidate.
3. Record the A review-contract decision and wire `report_states` in the fresh-A path so A real-source acceptance is structurally reachable.
4. Extend `tools/gate.sh` retained step (or layer audit) to execute/declare the full 18-file retained set; correct the checkpoint wording.
5. Add the small `valid_until`/future-time and visual-screenshot checks (P3-06, P2-04) with tests.
6. Add the trust-root paragraph to `design.md` and bind `expected_run_id` in the R6 acceptance checklist.
7. Then re-run the focused R2/runtime/preview/visual/real-source suite plus `tools/gate.sh` and record actual outputs.

Explicit unverified items:
- I did not execute tests, browsers, or the gate (read-only, no network); checkpoint gate counts (904/20/20/904) vs. gate scope are unresolved.
- Real independent-host receipt issuance, real Chromium/WebKit verdicts, and the real 24-portal matrix remain unverified by definition at this stage.
- Whether legacy (non-fresh) A/B/C entry paths still set `snapshot_locked` report states reachable by future runs was not fully traced (legacy DB evidence_state `source_research_service.py:1940-1953` is a different surface from run-manifest `report_states`).

Most important objections for Codex: (1) a promotion gate whose receipt is fabricated in every green test is not yet an *independence* gate — issuance must be productized before R2 closes; (2) promotion before the format node makes the runtime state machine able to certify not-yet-immutable candidates, and only the external acceptance ordering saves release integrity today; (3) A is structurally un-acceptable under the current shared boundary and needs an explicit decision, not drift; (4) the gate's "retained" claim overstates executed regression coverage. Decision points and bounded questions for Codex are embedded in steps 1–3 and the P1-01/P2-03 alternatives above.
