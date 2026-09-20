# Conference Participant Output: ci-r25-yaozh-browser-adapter-20260906-conference - general_single_object

## Boundary Check

- Worked inside runner CWD only (`.`). Read-only: no edits, no browser sessions, no credentials, no production writes.
- Sources used: `context/..._conference_context.md`, `plans/codex_main_venue_...md` (both near-empty TODO scaffolds — no usable decomposition or checklist), `.trellis/tasks/09-06-r25-yaozh-browser-adapter/{prd,design,implement}.md` + `task.json`, `reviews/codex_execution_ci-r25-yaozh-browser-adapter-20260906_review.md`, `src/ci_workflow/application/yaozh_access.py`, `capability_preflight.py`, `intake.py`, `run_service.py` (grep), `cli.py` (grep), `src/ci_workflow/domain/research_package.py`, `src/ci_workflow/gates/models.py` + `evaluator.py`, `policies/sources/source-policy-v1.yaml`, `policies/gates/{B,A}-v1.yaml` (grep), focused tests (`test_yaozh_access_cli.py`, `test_v13_intake_package.py`, others via grep).
- Worker outputs deliberately not read (per context §Source Of Truth). Did not perform visual/browser/clinical/regulatory acceptance — Codex-owned.
- Note: initial read set contained no decomposition, source packet detail, or verification checklist (TODO placeholders). This review proceeded on the context-declared source-of-truth list directly.

## Independent Work Product

### Disposition I endorse — and where I dissent on emphasis

Codex verdict (accept worker outputs as bounded input; **not** accepting R2.5 as complete; no RC/release signal) is correct. I independently confirm its "Open" list is real and would add one severity upgrade: the missing executable authority enforcement is not a follow-up nicety, it is the **P0 scientific-integrity hole** of this slice, because everything else (receipt, persistence, policy text) is now in place *around* an unenforced relabel path.

### Finding 1 (P0): Yaozh facts can be relabeled past the `commercial_database` tag at the gate-binding layer — enforcement is declarative, not executable

Evidence:
- `ResearchSource.source_role` now admits `commercial_database` with tight guards (`source_type` must be `secondary`, hostname must equal `vip.yaozh.com`) — `research_package.py:323-328`. Test pins approved-domain + type rejection (`test_v13_intake_package.py:263-287`).
- Gate vocabulary is a **different closed set**: `SourceRole` in `gates/models.py:77-87` has 7 values (`clinical_trial_registry`, `regulatory_material`, `primary_trial_report`, `protocol_sap`, `conference_disclosure`, `company_disclosure`, `designated_industry_source`). `commercial_database` is absent everywhere in `policies/gates/` (grep: zero hits outside `designated_industry_source`), and `RESULT_BEARING_SOURCE_ROLES` (`evaluator.py:66-75`, `models.py:236-243`) excludes it. So a correctly-tagged Yaozh source can never satisfy a gate unit or trigger `result_bearing` — by construction, good.
- But no code binds the two layers. Fact/provenance `source_role` at the gate layer is populated from extraction/fact lineage (`fresh_b_research_package.py`, `facts.py:source_role: str` free text), not from `ResearchSource.source_role`. An agent (or buggy adapter) that captures Yaozh page content and labels the resulting fact `designated_industry_source` — a result-bearing, gate-accepted role present in A/B units — bypasses the entire `commercial_database` corral without tripping any validator I found. Source-policy caps (`yaozh_enterprise`: never `direct`, at most `lead_only`/`cross_check`) similarly operate on the `yaozh_enterprise` source-id, not on content lineage; a relabeled fact sheds that identity.
- Codex already lists "executable Yaozh authority enforcement" as Open and deferred worker_03 D1–D4 as crossing A/B/C payload contracts. Confirmed: this is the right call, and the deferral must stay a **hard gate on R2.5 completion**, not a P2 polish item.

Remediation (smallest, TDD-shaped, no A/B/C contract redesign):
- Add a lineage map `commercial source_id (yaozh_enterprise / ResearchSource commercial_database) → gate SourceRole allowlist = {}` for result-bearing bindings, enforced where `GateEvidenceBinding` is built from fact provenance: reject any binding whose underlying `ResearchSource.source_role == commercial_database` yet whose gate `source_role` is result-bearing (especially `designated_industry_source`), plus a negative test (Yaozh-backed `b_core_efficacy_endpoint` / `b_safety_minimum_record` binding must fail closed). Keep D1–D4's broader redesign out of this slice.

### Finding 2 (P0-process): receipts persist but nothing consumes them — the route is currently dead, and the capability signal contradicts it

Evidence:
- `persist_yaozh_route_access_receipt` writes immutable content-addressed receipts (`state/yaozh-route-access/<observation_digest>.json`, same-bytes replay → `replayed=True`, digest conflict → fail closed) — `yaozh_access.py:314-341`. Solid.
- `RuntimeCapabilityProbe._check_real("login_browser")` unconditionally returns `(False, "宿主未提供可验证的已登录浏览器会话观察")` (`capability_preflight.py:251-252`). Blank-Chromium false readiness is indeed gone (confirmed fix).
- But grep shows **no consumer** of `state/yaozh-route-access/*` in `run_service.py` / `research_package_submission.py`: run only reads the one-time answer (`load_yaozh_access_record`, `run_service.py:588-595`) and hashes the answer file for node digests (`run_service.py:1539-1547`). A `ready` receipt therefore never flips any deterministic signal the agent can act on. The agent's only options are to ignore ready receipts (dead route) or improvise an ad-hoc bypass (unsafe route). Either outcome fails PRD exit intent ("会话有效时 Agent 可将药智页面转为…来源捕获").
- This matches Codex's "receipt-aware run integration" Open item. My upgrade: until that slice lands, R2.5 must report **route non-operational**, not "persistence done, integration pending" — the latter invites false readiness of a second kind (ceremonial receipts mistaken for working capability).

Remediation: explicit next slice — receipt-aware selection (`selection_from_project` + run work-item builder read latest `ready` receipt for the bound project/answer-digest **within a freshness window**; anything else keeps `login_browser` blocked/non-blocking). Until then, pause text must say the optional route is not yet runnable.

### Finding 3 (P1): ready receipts have no freshness bound — a stale observation reads as current session truth

Evidence: `YaozhSessionObservation._safe_observation` rejects naive datetimes and future > +1 min (`yaozh_access.py:126-130`); `build_yaozh_route_access_receipt` copies `observed_at`/`host`/`technical_state` with answer/project binding and closed action map (`:275-311`). Nowhere is a **maximum age** enforced. A `ready` observation from days ago yields a `ready` receipt today, contradicting PRD "运行期会话失效不改写该回答" + session-expiry semantics (a session valid at T0 says nothing at T1).
- Not exploitable for privilege (route is non-blocking, Yaozh never `direct`), but directly undermines "会话真值" — the headline promise of R2.5.
- Remediation: define `YAOZH_OBSERVATION_MAX_AGE` (Codex to set; suggest 24h, bounded question Q1), enforce at build time (`observation too stale → YaozhAccessError`), pin with negative tests (aged-ready rejected; fresh-ready accepted; boundary at exactly max-age).

### Finding 4 (P1): session truth is host attestation, not verifiable proof — `page_marker_sha256` is opaque

Evidence: `page_marker_sha256` is validated only as 64-hex (`yaozh_access.py:123`). Nothing binds it to actual page bytes; any host adapter can submit `ready` + arbitrary marker and receive a well-formed receipt. Origin is pinned to bare `https://vip.yaozh.com` with empty/`/` path only, no query/fragment/userinfo (`:131-141`; tests pin `/member`, `?token=x`, `http:` rejections). Consequence: the receipt attests *which domain* and *what claimed state*, never *which page* — two different pages produce indistinguishable origins, and the marker is unverifiable by core.
- This matches the design ("核心不接触浏览器 profile…只接受最小观察", `design.md:16-25`) — i.e., trust is intentionally placed in the host adapter + Codex controlled smoke. Acceptable architecture, but the PRD phrase "只有宿主实际观察到…已登录页面时才报告 ready" overstates what core enforces. Recommend relabeling in docs/pause notes: receipts are **authenticated host attestations**, not independent session proofs; the anti-forgery control is adapter allowlisting + Codex smoke custody, which has not yet run.
- Design tension to resolve (Q3): bare-domain origin deliberately sacrifices page identity for spoof-surface reduction. If page-level audit is wanted, add a separate `page_ref_sha256` with documented host-side derivation instead of widening `origin` paths.

### Finding 5 (P1, secret hygiene — residual, not a leak): token/value scanners are narrow; the wider channel is research-package content fields

What is good (verified):
- Observation/receipt models are `extra="forbid"`, frozen, 9–12 closed fields; receipt carries `credential_fields_allowed: False` and `blocks_core_research: False` as literals; `user_action_zh` is server-generated from a closed map — no host free text reaches the receipt.
- `project_id`/`observer_id` reject `/`, `\`, and 12 secret-adjacent tokens (`yaozh_access.py:142-155`); origin strict; `ResearchSource.url` rejects userinfo + secret query keys; recursive `_assert_safe_value` (`research_package.py:643-661`) rejects secret key names and `file://`-style local paths.
Gaps (residual, worth hardening before real smoke):
- `observer_id` token list misses bare `session`, `auth`, `otp`, `edge`, `profile`, `chrome`, `cdp`, `playwright` (only `sessionid` is covered). A host stuffing session material under an unlisted token name passes. Low exploitability today (no content channel in the receipt) but cheap to extend.
- `_SECRET_VALUE_RE` matches only prefixed values (`bearer/basic/BEGIN/JWT/AKIA`) — raw cookie strings, hex session ids, or base64 blobs in free-text fields (`ResearchSource.title/locator`, fact text) pass silently when the key name is innocent (e.g. `locator="SESSIONID=abc"`). If agents ever paste page text containing tokens, `_assert_safe_value` will not catch it. Recommend either extending value patterns (cookie-shaped `name=value;` pairs, 32+ hex runs in content fields — precision risk, needs tests) or, cheaper and sufficient for pause: a documented agent rule + smoke-checklist item ("never paste page text containing `Cookie/Set-Cookie/Authorization` values into any package field") plus a targeted test showing a cookie-shaped locator is rejected or flagged.
- CLI observe path (`cli.py:540-542`) validates via model but I did not verify symlink/permission handling of the *observation input file* itself (persistence side is careful: symlink/dir/file checks). Minor; note for the hardening pass, not a blocker.

### Finding 6 (P2 / verification): damaged-record handling is half-typed

Evidence: `_read_validated_record` raises typed `YaozhAccessError` with closed Chinese messages and never re-asks (`yaozh_access.py:195-213`) — good. But `load_yaozh_access_record` propagates on damaged files, and the run work-item builder calls it without a visible typed catch (`run_service.py:588-595`); the preflight node only hashes the answer file (`:1539-1547`) without validating. A tampered record mid-run likely surfaces as an unhandled error rather than the designed fail-closed diagnostic. Codex's "typed damaged-record handling" Open item stands; recommend one test (corrupt `state/yaozh-access.json` → deterministic Chinese fail-closed, no re-ask, no resume past preflight) as part of the enforcement slice.

### Scope integrity

- `yaozh_enterprise` policy (`source-policy-v1.yaml:70-83`): not baseline, not required-for-China, `authoritative_secondary: false`, no `direct` in any domain, `lead_only` on efficacy/safety results — consistent with PRD "只用于线索与交叉核验". No escalation via policy text.
- B-v1 sampled units + full grep: `commercial_database`/`specified_secondary` absent from all gate `allowed_source_roles`; `designated_industry_source` present in result-bearing units — which is exactly why Finding 1's relabel path matters (the confusingly-similar name is one typo away from an escalation).
- PRD exclusions respected in code: no credential storage, no profile copy, no captcha bypass (action strings explicitly refuse bypass), no Playwright/CDP in core (`login_browser` short-circuits before any browser import; Playwright only under `search_browser`/`browser_validation`), Yaozh never required (`required_for_core_research is False`, `route.required is False` in integration tests).
- Pause status is truthful **only if** stated as: false-positive eliminated; persistence + secret minimization + non-escalation-by-construction landed; **route not yet operational** (no consumer, no freshness, no executable enforcement, no real smoke, no full regression). Codex review says this; the R2.5 task file should say it verbatim so a successor doesn't read "39 tests passed" as readiness.

## Evidence And Assumptions

Evidence (observed):
- `yaozh_access.py:59-156` (receipt + observation models, validators); `:159-193` (digest/atomic-write/record-bytes helpers); `:195-272` (record validation, project binding, once-only answer); `:275-341` (receipt build/persist, idempotent replay, conflict fail-closed).
- `capability_preflight.py:142-279` (`login_browser` fail-closed; blank-Chromium path retained only for `search_browser`/`browser_validation`).
- `research_package.py:227-328` (`commercial_database` role + guards); `:629-661` (secret/local-path scanners).
- `gates/models.py:77-87, 236-243`, `evaluator.py:66-75` (7-role closed vocabulary; Yaozh role absent by construction).
- `policies/sources/source-policy-v1.yaml:70-83` (Yaozh caps); `policies/gates/{B,A}-v1.yaml` grep (no `commercial_database` in any unit).
- `intake.py:190-267` (once-only answer, optional-route decision); `run_service.py:588-595, 1539-1547` (answer consumed, receipts not); `cli.py:534-543` (observe entry).
- Tests: `test_yaozh_access_cli.py:294-454` (state separation, secret/origin rejection, idempotent persist); `test_v13_intake_package.py:263-335` (role guard, schema-model parity).
- Codex review verdict + Open list; R2.5 prd/design/implement intent.

Inference (flagged as such):
- [INFERENCE] No intake→gate lineage check exists — based on grep over `src/ci_workflow` for `commercial_database` (only `research_package.py` + its test) and free-text `source_role: str` in `facts.py`. A dedicated cross-layer validator could exist under an ungrepped name; Codex should confirm, but its own "absent executable source-authority enforcement" admission corroborates.
- [INFERENCE] Real-smoke custody and full gate/bundle regression have not run — per Codex Open list; I did not re-run suites (read-only review role; running them would also be legitimate verification for the enforcement slice, not this pass).

## Risks, Gaps, And Verification Needs

| # | Risk | Severity | Verification needed |
|---|------|----------|---------------------|
| 1 | Yaozh content relabeled as `designated_industry_source` at fact/provenance layer bypasses all R2.5 guards | P0 | Negative test: Yaozh-lineage fact → result-bearing binding must fail closed; add lineage allowlist check at binding build |
| 2 | Ready receipts have no consumer; `login_browser` always blocked → dead route or ad-hoc bypass | P0-process | Receipt-aware selection slice + test (ready+fresh ⇒ route actionable; else blocked-non-blocking); until then declare route non-operational |
| 3 | No receipt freshness bound; stale `ready` reads as current truth | P1 | Max-age enforcement + boundary tests |
| 4 | `page_marker_sha256` opaque; receipts are host attestations, not proofs | P1-docs | Relabel in docs/pause notes; resolve origin-granularity question (Q3) |
| 5 | Secret scanners narrow (observer_id tokens; value-prefix-only; content-field channel) | P1 | Extend token list; cookie-shaped content test or agent rule + smoke-checklist item |
| 6 | Damaged answer record mid-run may surface unhandled instead of designed fail-closed | P2 | Corrupt-record test through run preflight path |
| 7 | `origin` restricted to bare domain loses page identity for audit | P2-design | Q3 decision; do not widen without marker-derivation spec |

## Recommended Next Step

1. **Do not mark R2.5 complete.** Keep `in_progress`; append a pause note stating verbatim: route non-operational pending (a) executable Yaozh→gate lineage enforcement with negative tests, (b) receipt-aware run integration + freshness window, (c) typed damaged-record path test, (d) Codex-custody real smoke with desensitized receipts only, (e) full gate/bundle regression.
2. Smallest next slice (TDD, no A/B/C redesign): lineage-enforcement + freshness + consumer wiring in that order; each with one negative test. Estimated surface: `yaozh_access.py` (max-age), binding-build site (lineage check), `capability_preflight.selection_from_project` + work-item builder (receipt read), plus 4–6 focused tests.
3. Bounded questions for Codex:
   - **Q1 (freshness):** What max age should a `ready` observation carry (suggest 24h)? Should expiry downgrade the receipt's interpretation to `session_expired`-equivalent, or simply make selection ignore it?
   - **Q2 (lineage ground truth):** Is the canonical Yaozh-lineage marker `ResearchSource.source_role == commercial_database`, `source_id` prefix, or the `yaozh_enterprise` policy id — and must `designated_industry_source` facts carry proof of non-Yaozh lineage?
   - **Q3 (origin granularity):** Keep bare-domain `origin` (current) and accept page-unverifiable attestations, or add a specified `page_ref` derivation (host adapter hashes normalized page URL + marker) while keeping `origin` bare?
   - **Q4 (smoke sequencing):** Should controlled real-host smoke run before the enforcement slice (to validate adapter behavior early, receipts quarantined) or strictly after (no real sessions until enforcement lands)? Safe provisional path I recommend: **after** — there is currently no consumer that could use a smoke receipt, and no enforcement quarantining misuse of smoked content.
