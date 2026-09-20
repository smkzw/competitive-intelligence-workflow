# Execution Output: ci-r25-yaozh-browser-adapter-20260906 - worker_03

## Boundary And Context Check

- Role: `worker_03`, task `ci-r25-yaozh-browser-adapter-20260906`, assigned work item 3 only: *design research-package and source-policy integration plus negative tests proving Yaozh remains optional lead/cross-check and cannot become sole evidence for critical claims*. Execution manager: none; Codex reviews directly.
- Read set honored: `context/ci-r25-yaozh-browser-adapter-20260906_execution_context.md`, `plans/codex_execution_ci-r25-yaozh-browser-adapter-20260906.md`. Additional reads (justification: the context names these files as implementation truth and requires every finding to cite current file/symbol): `policies/sources/source-policy-v1.yaml`, `src/ci_workflow/sources/policy.py`, `src/ci_workflow/domain/research_package.py`, `src/ci_workflow/application/{autonomous_research,intake,yaozh_access,capability_preflight,research_package_submission,source_research_service,fresh_b_research_package}.py` (targeted sections), `src/ci_workflow/gates/models.py` (targeted sections), `src/ci_workflow/gates/evaluator.py` (targeted sections), `docs/specs/competitive-intelligence-workflow-design-v1.3.md` (§3.2 lines 153–166, §5.1 lines 250–259, §5.3 lines 276–278, D71 line 97), `tests/unit/test_source_policy.py`, `tests/integration/test_autonomous_research_work_item.py`, `tests/contract/test_v13_intake_package.py`, `policies/gates/A-v1.yaml` (head).
- Read-only pass observed: no file created, modified, or deleted anywhere in the workspace; no tests run (context declares this an analysis pass; test *execution* adds no evidence for a design artifact and was not assigned). No browser session opened, no credentials, no production paths, no legacy workspace access.
- Report returned in this message only; runner persists `runs/execution/ci-r25-yaozh-browser-adapter-20260906/worker_03.md`.

## Work Performed

I mapped the full current Yaozh integration chain (policy YAML → policy model → intake record → autonomous-research route planning → package domain → payload validators → gate evaluator → submission boundary), then located the exact fail-closed gaps and designed the smallest typed integration plus a negative test matrix. Findings below separate **evidence** (file:line in the current dirty tree) from **inference** and **recommendation**.

### A. Current state — what already holds (evidence)

1. **Policy declaration is correct.** `policies/sources/source-policy-v1.yaml:70-83` (`yaozh_enterprise`): no `direct` authority in any of the 8 claim domains; `lead_only` for `efficacy_safety_results`, `baseline_disposition`, `patents_protection`; `cross_check` for the other five; `required_global_baseline: false`, `required_for_china: false`, `authoritative_secondary: false`. Contract anchor: design v1.3 lines 163–165 (“药智的临床数值降为 `lead_only`，其他适用声明域最多为 `cross_check`；任何药智内容都不能成为…唯一依据”) and §5.3 lines 276–278.
2. **Policy model is closed.** `src/ci_workflow/sources/policy.py:92-148` — `SourceDefinition._all_claim_domains_are_explicit` (all 8 domains explicit), `SourcePolicy._matrix_is_complete_and_unique`, `authority_for(source_id, domain)`.
3. **YAML floor is already unit-tested.** `tests/unit/test_source_policy.py:72-82` asserts yaozh is never `DIRECT`, efficacy is `LEAD_ONLY`, and neither required flag is set.
4. **Route planning already keeps Yaozh optional and out of expansion.** `src/ci_workflow/application/autonomous_research.py:145-150` (`_direct_sources` — yaozh can never appear in expansion/report route source lists because it is never `direct`); `:217-231` — the `yaozh-optional-browser` route is appended only when `yaozh_record.answer == "available"`, with `required=False`. `tests/integration/test_autonomous_research_work_item.py:34-70` covers both directions.
5. **One-time answer, closed record, idempotent replay.** `src/ci_workflow/application/intake.py:187-253` (`YaozhAccessRecord`, `record_yaozh_answer`, `YaozhAskAlreadyAnswered`); persistence fail-closed on symlink/tamper/identity mismatch in `src/ci_workflow/application/yaozh_access.py:93-159` (`answer_yaozh_access`, `_read_validated_record`).
6. **Typed runtime access receipt exists (worker_02 territory, already implemented).** `yaozh_access.py:50-71` `YaozhRouteAccessReceipt` — `technical_state ∈ {ready, session_expired, tool_unavailable}`, `result_class ∈ {ready, access_blocked}` with state↔result coherence, `blocks_core_research: Literal[False]`, `credential_fields_allowed: Literal[False]`, `answer_digest` binding via `build_yaozh_route_access_receipt` (`:173-192`). Note: captcha/permission have no dedicated `technical_state` (they surface only as `RouteReceipt` result classes, see G6).
7. **Capability preflight treats login browser as optional.** `src/ci_workflow/application/capability_preflight.py:503-516` (blocked optional route → non-blocking Chinese message), `:622-649` (`selection_from_project` adds `authenticated-browser` only when the record is `route_enabled`).
8. **Package hygiene for secrets/paths already enforced.** `src/ci_workflow/domain/research_package.py:623-655` (`_SECRET_KEY_RE`, `_SECRET_VALUE_RE`, `_LOCAL_PATH_RE`, recursive `_assert_safe_value` applied to the whole package at `:702`); URL credential rejection at `:280-290`.
9. **Submission binds payload to envelope.** `src/ci_workflow/application/research_package_submission.py:121-135` (payload sources ⊆ envelope sources, attempts ⊆ envelope attempts), `:274-279` (policy id/version equality).

### B. Fail-closed gaps (evidence → why the contract is not yet enforced)

- **G1 — the authority matrix has no executable consumer.** `rg -n "authority_for"` across `src` and `tests`: defined at `sources/policy.py:145-148`, consumed only by `tests/unit/test_source_policy.py`. No application or gate code consults the policy when admitting evidence. The "lead/cross-check only" property of Yaozh is declarative, not enforced. *(Evidence: the empty result of the grep documented in Commands And Observations.)*
- **G2 — package sources are not policy-closed.** `ResearchPackage._references_and_safety_are_closed` (`research_package.py:700-966`) checks only internal referential closure; `ResearchSource.source_id` (`:227-322`) is any non-blank string. A package citing `yaozh_enterprise` — or an invented id — with any `source_role` (including `primary_publication`) passes `validate_research_package`. `submit_product_research_package` checks only `source_policy_id`/`version` equality (`research_package_submission.py:274-279`), never membership.
- **G3 — the sole-evidence prohibition is prose.** The contract sentence exists only as completion/guidance strings: `autonomous_research.py:227-229` (“不得作为关键结论的唯一依据”)， `intake.py:261` (“核心数值仍需适格官方来源”). No typed invariant is evaluated at admission or gate time.
- **G4 — provenance `source_role` is host-declared without an authority cross-check (authority-escalation path).** `BFactProvenance` (`fresh_b_research_package.py:170-215`) carries `source_id` and `source_role: SourceRole` side by side; nothing validates the pairing against the policy. A yaozh-backed fact declared `source_role=primary_trial_report` or `designated_industry_source` satisfies critical units through `evidence_binding_qualifies` (`gates/models.py:1565-1592`, role check at `:1586`) and `_RESULT_BEARING_SOURCE_ROLES` (`gates/evaluator.py:66-77`). Same shape in A (`ResearchFact.source_id`, `source_research_service.py:88-110`) and C (`GateEvidenceBinding` built at `fresh_c_research_package.py:493`).
- **G5 — no binding between the package and the project's Yaozh answer.** `submit_product_research_package` never loads `state/yaozh-access.json`; a project that answered `skipped`/`unavailable` can submit a package containing `yaozh_enterprise` sources or a `yaozh-optional-browser` route receipt.
- **G6 — package route receipts do not bind runtime session truth (false readiness).** `RouteReceipt` (`research_package.py:325-388`) accepts `captcha_required`/`permission_denied` but has no linkage to `YaozhRouteAccessReceipt.answer_digest`; a package can claim completed yaozh routes while the runtime receipt says `session_expired`. Conversely, nothing prevents an optional yaozh route id from being placed into `UniverseClosure.global_route_ids`/`china_route_ids` except the manual planner — validator-side, closure routes just need to exist and be terminal (`research_package.py:975-988`).
- **G7 (minor) — `ExtractionCandidate.claim_domain` is optional free text** (`research_package.py:522-540`), unconstrained against `ClaimDomain`, so it cannot currently support a support-level computation.

### C. Recommended integration design (recommendation, anchored in v1.3)

Design principles: smallest typed change; fail-closed; reuse `SourcePolicy` as the single authority truth; **no yaozh-specific branching in engine code** — yaozh is merely the only source whose maximum authority is below `direct` in every domain, so the general authority floor covers it and any future source automatically.

**D1 — New pure module `src/ci_workflow/sources/authority.py`** (no I/O; mirrors `sources/policy.py` layering; application and domain may import it without cycles):

- `SUPPORT_LEVELS: direct > cross_check > lead_only > not_applicable`.
- `domain_support(policy, domain, source_ids) -> SupportLevel` — max authority over the cited set for that domain.
- `assert_claim_bearing_support(policy, domain, source_ids)` — for an **accepted fact** (`disclosure_state ∈ {reported_value, reported_zero}`):
  - a `lead_only`-authority source is forbidden outright (lead material may only live in `UniverseExpansionReceipt.source_ids` and identity/alias leads — per policy v1.1 semantics and v1.3 §5.3 “数值疗效和安全性不得直接采纳，只能用于定位线索”)；
  - support with no `direct`-authority source in the cited set is forbidden (`insufficient authority`), i.e. cross_check-only support cannot settle a claim.
- Mapping table `FACT_DOMAIN_TO_CLAIM_DOMAIN`: `efficacy → efficacy_safety_results`, `safety → efficacy_safety_results`, `trial_design → trial_identity_design_status` (`FactDomain` is exactly these three — `gates/models.py:148-153`). B-baseline rows need a secondary key (see Assumptions).
- Package source profiles `PACKAGE_SOURCE_PROFILES: dict[str, tuple[source_type, source_role]]` pinning each policy `source_id` to its allowed package role pair (for `yaozh_enterprise`: `("secondary", "specified_secondary")`; for registries: `("registry", "official_registry")`; etc.). Kills role misdeclaration at envelope level (G2/G4).

**D2 — Envelope closure at submission** (`research_package_submission.submit_product_research_package`, insert after the policy version check at `:274-279`):

1. Every `package.sources[].source_id` must resolve in the loaded policy; every source's `(source_type, source_role)` must equal its profile entry.
2. If the package cites `yaozh_enterprise` anywhere (sources, routes, expansion receipts), require `load_yaozh_access_record(project_root)` present with `route_enabled is True`; otherwise fail closed (G5).
3. Any `RouteReceipt` with `route_id == "yaozh-optional-browser"` must bind the runtime receipt digest (worker_02's `YaozhRouteAccessReceipt.answer_digest`, `yaozh_access.py:188`) in package metadata; the submission recomputes sha256 over `state/yaozh-access.json` and compares (G6 join point; credential-free, idempotent).
4. Reject a package whose `UniverseClosure.global_route_ids`/`china_route_ids` contain `yaozh-optional-browser` — the optional route must never be load-bearing for closure.

**D3 — Payload-level authority floor** (A/B/C content validators, the chokepoints where `source_id` is already present):

- A: in `FreshAResearchContent._content_is_closed` (`source_research_service.py:1504-1617`), for every fact with `reported_value`/`reported_zero`, run `assert_claim_bearing_support` over its `source_id` and family-mapped domain. `AtomicFact.source_id` is scalar (`:98`), so for single-source facts "sole evidence" is exactly that one source.
- B: same check over `BFactProvenance` (`fresh_b_research_package.py:170-215`) and `BFactReviewBinding` (`:418-430`).
- C: over the bindings built at `fresh_c_research_package.py:493` via their provenance.
- Effect: yaozh alone can never back an accepted numeric fact; for `lead_only` domains (efficacy/baseline/patents) even co-support with a direct source is rejected; for `cross_check` domains (e.g., `regulatory_development_status`) yaozh may corroborate alongside a `direct` source — which is precisely the v1.3 contract split.

**D4 — Gate-level floor (defense in depth).** Pass a `fact_version_id → source_ids` projection (derivable from existing A facts / B provenance without changing any payload schema) into unit evaluation and extend `evidence_binding_qualifies` (`gates/models.py:1565`) or `evaluate_unit_decision`: a **critical** unit is satisfied only if ≥1 qualifying accepted binding's source set contains a `direct`-authority source for the unit's mapped claim domain; lead-only-sourced bindings never count as satisfying evidence. Surface a new failure code `insufficient_source_authority` through the existing `GateUnitResult`/`ReportGateResult` aggregation (`gates/models.py:743+`), so the report blocks with a Chinese user action instead of silently passing. This layer protects against future payload families missing the D3 check. No change to `GateEvidenceBinding` fields, no change to `policies/gates/*.yaml`, no payload `content_schema_version` bump needed in this variant.

**D5 — Contract separation (explicit non-goals for this item):**
- No change to the once-only `YaozhAccessRecord` semantics, no credential surface; the receipt remains digest-only (worker_02's contract is the authority there).
- No change to the policy YAML authorities — the current matrix already encodes the contract; lock it with a guard test (T12 below) instead.
- Expired-session/captcha/permission *runtime detection* against the real `vip.yaozh.com` host is real-host smoke, explicitly deferred; this design covers only the portable contract and its negative tests.
- Follow-through if Codex accepts D2.3 metadata: update `schemas/research-package.schema.json` and the format contract docs in the same change set; keep additions additive/optional to avoid bumping `ReportPayloadBinding.content_schema_version` (`research_package.py:167-193`).

### D. Negative test matrix (the assigned deliverable)

Placement proposal: pure-function tests in `tests/unit/test_source_authority.py` (new); envelope/submission tests next to the existing submission/yaozh integration tests (`tests/integration/`); payload-level tests in the existing contract test modules (`tests/contract/`); gate-level test next to existing gate evaluator tests. Exact files follow existing conventions at implementation time.

| # | Test | Arranges → asserts | Gap closed |
|---|------|--------------------|------------|
| T1 | `test_yaozh_only_numeric_fact_is_rejected` | A/B payload fact, `source_id=yaozh_enterprise`, `disclosure_state=reported_value` (efficacy/safety family) → validation rejects; no report generated | R2: lead_only floor (G1/G3) |
| T2 | `test_cross_check_only_support_is_rejected` | `regulatory_development_status` claim supported by `{yaozh_enterprise, dxy_drug_assistant}` (both cross_check, no direct) → `insufficient authority` rejection | sole-evidence rule (G3) |
| T3 | `test_cross_check_plus_direct_support_is_admitted` | same claim + `cde` (direct for that domain) → passes; proves cross_check corroboration stays usable | optionality preserved |
| T4 | `test_package_source_outside_policy_fails_closed` | invented `source_id` (e.g. `yaozh_vip_mirror`) → submission error | G2 |
| T5 | `test_misdeclared_source_role_fails` | yaozh source declared `source_role=primary_publication` → profile mismatch error | G4 envelope half |
| T6 | `test_yaozh_citation_requires_enabled_route` | record answer=`skipped` + package citing yaozh → rejected; same bytes with answer=`available` → admitted; resubmit identical package → `replayed=True` | G5 + idempotency |
| T7 | `test_route_receipt_digest_binds_session_truth` | package claims yaozh route completed; digest over tampered `state/yaozh-access.json` mismatches `answer_digest` → rejected; fabricated ready receipt with wrong digest → rejected | G6 / **false browser-readiness** |
| T8 | `test_blocked_technical_states_stay_non_blocking` | `build_yaozh_route_access_receipt` with `session_expired` and `tool_unavailable` → `result_class=access_blocked`, `blocks_core_research` is literally `False`, zh guidance present; capability matrix research readiness remains `ready` (`capability_preflight.py:503-516`) | **expired/tool states** |
| T9 | `test_captcha_and_permission_route_states_terminate_without_blocking` | `RouteReceipt` for yaozh route with `captcha_required` / `permission_denied` + diagnostic → `assert_gate_ready` accepts them as terminal only for the *optional* route; overall gate still passes from other routes; yaozh route id in closure route sets → rejected | **captcha/permission states** + optional-not-load-bearing |
| T10 | `test_secret_and_path_rejection_for_yaozh_materials` | package metadata/diagnostics containing `{"cookie": …}`, `Bearer ey…`, `/Users/x/state.json`, URL with `?session_token=` → `_assert_safe_value` / `_external_url` rejections (`research_package.py:280-290, 623-655`) | **secret/path rejection** |
| T11 | `test_answer_and_submission_idempotency` | `answer_yaozh_access` same-answer replay idempotent (`yaozh_access.py:136-148`); identical package resubmission → `replayed=True`, never a second ask (`YaozhAskAlreadyAnswered` not raised) | **idempotency** |
| T12 | `test_policy_authority_lock_no_escalation` | extended guard: yaozh authorities ⊆ {lead_only, cross_check, not_applicable}, `authoritative_secondary is False`, required flags False, **and** `build_autonomous_research_task` never returns yaozh in any route/expansion source list for any answer | **no authority escalation** (extends `test_source_policy.py:72-82`) |
| T13 | `test_skipped_yaozh_project_completes_core_research` | full yaozh-free package from a `skipped` project passes gate-ready + submission | `blocks_core_research=False` honored; Yaozh optional end-to-end |
| T14 | `test_expansion_lead_usage_is_preserved` | yaozh in `UniverseExpansionReceipt.source_ids` with discovered entities → admitted (negative-space: the floor must not over-block leads, per §5.3 适应症扩展轨迹) | optionality of lead role |
| T15 | `test_critical_unit_with_only_yaozh_sourced_bindings_fails` | gate evaluation where every qualifying binding of a critical unit is yaozh-sourced → unit fails with `insufficient_source_authority`, report blocked, no silent downgrade | D4 defense-in-depth |

Each test is deterministic and offline (fixture packages in the style of `fixtures/positive/a-atopic-dermatitis/`); no real Yaozh host, no credentials, per the risk boundaries.

## Artifacts And Evidence

- No files created or modified (read-only pass; runner persists this report).
- The deliverable is the design above: gap analysis G1–G7 with file:line evidence; integration design D1–D5 (new `sources/authority.py`, envelope closure in `research_package_submission.py`, payload floors in the A/B/C validators, gate-level `insufficient_source_authority`); negative test matrix T1–T15 covering false browser-readiness, expired/captcha/permission/tool states, secret/path rejection, idempotency, and no-authority-escalation as required by the context's completion-evidence clause.
- Cross-worker dependency: D2.3 consumes worker_02's `YaozhRouteAccessReceipt.answer_digest` (`yaozh_access.py:50-71,188`) as the credential-free join key; if worker_02's final contract renames that field, only the D2.3 metadata field name changes.

## Commands And Observations

- `rg -l "source_policy|SourcePolicy" src` → consumers: `sources/policy.py`, `application/{research_package_submission,run_service,autonomous_research}.py`, `sources/connectors/{authoritative_wechat,china_registries}.py`, `domain/research_package.py`.
- `rg -n "authority_for|SourceAuthority|authoritative_secondary|lead_only|sole" src tests --type py` → **no application/gates consumer of the authority matrix**; only `sources/policy.py` (definition), `autonomous_research.py:145` (`_direct_sources`, planning-time only), and `tests/unit/test_source_policy.py`. This is the primary evidence for G1.
- `rg -n "authority.*source_role|policy.*source_role" src/ci_workflow/application src/ci_workflow/gates` → **empty result**; primary evidence for G4.
- Read commands on the files listed under Boundary And Context Check (Read/sed on targeted ranges); no state-changing command was run; git tree untouched.

## Blockers Or Missing Environment

- No blockers. No missing tools; no package installation attempted; no environment changes.
- Assumptions recorded for Codex: (a) `FactDomain` is exactly {trial_design, efficacy, safety} (`gates/models.py:148-153`), so B **baseline** facts cannot be domain-keyed by `FactDomain` alone — D3 must key baseline rows by their unit family (`b_baseline_*` per `_baseline_unit_id`, `fresh_b_research_package.py:960-978`) or row family; inference, verified against the enum but not against every B unit. (b) Payload additions are kept additive/optional so `content_schema_version` stays "1.0"; if Codex prefers required fields instead, the version literal must be bumped in the same change set. (c) The current dirty tree was preserved; line numbers refer to this tree state and may shift after concurrent worker-driven edits.

## Rerun Requests Or Next Step

- No rerun needed for this item; the pass is complete within its boundaries.
- Precise questions for Codex (decisions only Codex owns): (1) accept D2.3's digest-binding metadata field into the audit package schema (additive) or defer digest binding to worker_02's receipt surface only; (2) accept the `insufficient_source_authority` failure code as a new gate failure code, or fold it into the existing `missing_required_evidence` code to avoid touching failure-code contracts; (3) whether T12's policy lock should also freeze the full authorities matrix byte-for-byte (stronger, but hard-couples the test to future policy evolution).
- Next steps after Codex acceptance: implement D1–D4 with TDD in the listed files (Codex-owned), then a separate real-host smoke item for actual session expiry/captcha behavior — out of scope for this design pass.
