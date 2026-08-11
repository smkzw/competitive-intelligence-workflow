# Task 1.1 Independent Acceptance

## Tests And Probes

**Read set (this recovery + same session):**  
`ids.py`, `enums.py`, `contracts.py`, `schemas/project-contract.schema.json`, `tests/unit/test_ids.py`, `tests/unit/test_state_enums.py`, `tests/contract/test_project_contract.py`, `package-manifest.json`, `docs/decisions/0004-phase-1-contract-boundaries.md`.

**Live pytest this recovery turn:** not obtained (prior shell invocations in-session were cancelled). Verdict is based on full static audit of the listed implementation/tests/schema/manifest plus language-defined Python `Enum` construction semantics. Source-packet historical anchor (not re-run here): target suite GREEN; do **not** treat that count as acceptance.

| ID | Probe / check | Method | Observed / deduced result |
|---|---|---|---|
| T1 | `test_task_1_1_stable_ids_...` | Static: asserts match `stable_id` | Would pass: whitespace collapse, namespace split, empty part `ValueError` / `不能为空`, `product_[0-9a-f]{24}` |
| T2 | `test_task_1_1_freezes_all_nine_state_families_...` | Static vs `enums.py` | Would pass: nine sets exact; cross-type member `!=`; `FactDisclosureState("")/0/None` raise; `FactDisclosureState(RouteAttemptResult.TRANSIENT_NETWORK_FAILURE)` raises |
| T3 | `test_contract_has_version_timezone_...` | Static vs `create_project_contract` | Would pass: default cutoff EOD `+08:00`; historical `America/New_York` leap day `-05:00`; HTML prepended; invalid `Shanghai` rejected at factory; schema validates factory dump |
| T4 | `test_default_cutoff_is_fixed...` | Static vs resume/refresh | Would pass: `resume is` same object; cutoff frozen; refresh v2 later cutoff; old object unchanged; non-increasing cutoff raises |
| P1 | `stable_id("product","  ABC-123  ","CRSwNP")` vs trimmed / `trial` / `ABC-124` | Code path | Deterministic; namespace and material differentiate; empty part rejected |
| P2 | `stable_id("product","")` / missing parts / bad kind | Code path | Empty identity → `ValueError`; bad kind → pattern error (message differs from identity-empty) |
| P3 | Shared-value cross-enum: `FactDisclosureState(RouteAttemptResult.NOT_PUBLICLY_DISCLOSED)` | Python `Enum` value lookup | **Succeeds** → `FactDisclosureState.NOT_PUBLICLY_DISCLOSED` (not covered by T2) |
| P4 | Shared-value cross-enum: `ReportEvidenceState(ProjectRunState.AWAITING_USER)` / `DownloadRequestState(ProjectRunState.AWAITING_USER)` | Same | **Succeed** (value `"awaiting_user"`) |
| P5 | Shared-value: `FormatArtifactState(ReportEvidenceState.QUEUED)` / `.SUPERSEDED`; `FormatArtifactState(ProjectRunState.BLOCKED)` | Same | **Succeed** on `"queued"` / `"superseded"` / `"blocked"` |
| P6 | Naive/offset `created_at` / `data_cutoff` on model | Validators | Naive rejected; offset required |
| P7 | Default/explicit cutoff day-end in declared zone | `datetime.combine(..., time.max, tzinfo=zone)` | Materializes local EOD with zone offset; future local date rejected |
| P8 | Resume next day | `resume_project_contract` returns input | No recompute of cutoff; identity preserved |
| P9 | Refresh expand / non-expand | `refresh_project_contract` | New version +1; same `project_id`; original frozen object intact; `cutoff <= current` rejected |
| P10 | Schema-only `timezone: "Shanghai"` | JSON Schema properties | **Accepts** (`minLength: 1` only); Pydantic/factory **rejects** |
| P11 | Schema-only `outputs: ["pdf","html"]` | Schema `contains`+`enum` | **Accepts** (HTML present, not forced first); Pydantic `_outputs_start_with_html...` **rejects** unless `html` is index 0 |
| P12 | Schema-only naive `data_cutoff` / `created_at` | `format: date-time` annotation | Format not a hard gate in typical Draft 2020-12 use; no `pattern` requiring offset; Pydantic enforces offset |
| P13 | Manifest registration | `package-manifest.json` `components.schemas` | **Registered:** `schemas/project-contract.schema.json` |

## Findings

**Evidence (from listed sources):**

1. **Stable IDs (`ids.py`)**  
   - Kind: NFKC → strip/collapse → `casefold` → `^[a-z][a-z0-9-]*$`.  
   - Parts: NFKC → strip → whitespace collapse; empty after normalize rejected.  
   - Payload: `kind` + parts joined by `\x1f`, SHA-256 truncated to 24 hex, prefix `{kind}_`.  
   - Matches ADR: deterministic, namespaced, non-empty identity materials.  
   - Tests cover whitespace, namespace, emptiness; not homoglyph/control-char matrix (implementation still applies NFKC).

2. **Nine state families (`enums.py`)**  
   Members match the freeze in `test_state_enums.py` for:  
   `RouteAttemptResult`, `RouteCompletion`, `FactDisclosureState`, `FactReviewState`, `ProjectRunState`, `ReportEvidenceState`, `FormatArtifactState`, `DownloadRequestState`, `RevisionApprovalState`.  
   Also present: `ReportKind` (A/B/C), `OutputFormat` (html/pdf/html-ppt/pptx).  
   Plain `Enum` (not `IntEnum`): `""` / `0` / `None` cannot stand in as disclosure states.  
   Cross-family **member** inequality holds (`ProjectRunState.AWAITING_USER != ReportEvidenceState.AWAITING_USER`).

3. **Project choices (`contracts.py` + schema)**  
   - Reports: non-empty, unique, only A/B/C (factory + model).  
   - Outputs: factory always forces `html` first then optional pdf/html-ppt/pptx, deduped; model requires `outputs[0] is HTML` and uniqueness.  
   - HTML default behavior satisfied on factory path; ADR “HTML 始终进入输出” met for `create_project_contract`.

4. **IANA timezone**  
   - Factory and model use `ZoneInfo`; invalid IANA → `ValueError` / “IANA”.  
   - Default `"Asia/Shanghai"`.  
   - Schema does **not** validate IANA (string minLength only).

5. **Cutoff materialization**  
   - Local calendar date (default = create local date, or parsed date/datetime in zone) → `23:59:59.999999` in declared zone.  
   - `cutoff_was_user_supplied = (cutoff is not None)`.  
   - Cutoff after create local date rejected.

6. **Resume**  
   - Returns the same frozen instance; `resumed_at` validated if given but **does not** alter scientific fields. Cross-day recovery does not drift cutoff.

7. **Refresh**  
   - Builds a **new** `ProjectContract` with `contract_version + 1`, same `project_id`/reports/outputs/timezone/indication, later cutoff only, does not mutate prior object. Matches “扩大 cutoff 只能形成新版本”.

8. **Pydantic ↔ JSON Schema ↔ package**  
   - Required fields largely aligned; `additionalProperties`/`extra=forbid` aligned; report/output enums aligned.  
   - Gaps: IANA enforcement; outputs **order** (html-first vs contains-only); offset-hard requirement.  
   - Package manifest **does** list `schemas/project-contract.schema.json`.

**Inference:**

- Shared **value strings** across independent scientific/process axes are the highest-impact defect: Python `Enum(x)` resolves by **value**, so a route/run enum member with a colliding string coerces into another family. That is exactly the “状态混写” class ADR forbids (“路由失败不能写入事实披露列” and non-substitutable families). Tests only probe a **non-colliding** route value.  
- Schema-only validation is weaker than the runtime contract; dual-path ingest can accept payloads the domain model will reject (or, if schema is sole gate later, accept scientifically loose timezone/cutoff/order).

**Uncertainty:**

- Live suite not re-executed this turn.  
- Design v1.2 §3.1/§8.4/§10.2 member wording not in this round’s read list; membership acceptance is against ADR + in-repo enum freeze tests, not a fresh line-by-line design extract.

## P0/P1 Defects

### P0-1 — Cross-family enum value coercion (scientific state mix-write)

| | |
|---|---|
| **Where** | `src/ci_workflow/domain/enums.py` — shared `.value` strings across families; construction via stdlib `Enum` |
| **Reproducible input** | `from ci_workflow.domain.enums import FactDisclosureState, RouteAttemptResult` then `FactDisclosureState(RouteAttemptResult.NOT_PUBLICLY_DISCLOSED)` → `FactDisclosureState.NOT_PUBLICLY_DISCLOSED` |
| **Also** | `ReportEvidenceState(ProjectRunState.AWAITING_USER)`; `FormatArtifactState(ReportEvidenceState.QUEUED)`; `FormatArtifactState(ProjectRunState.BLOCKED)`; `DownloadRequestState(ProjectRunState.AWAITING_USER)` |
| **Colliding values (non-exhaustive)** | `not_publicly_disclosed` (route ↔ fact disclosure); `awaiting_user` (run ↔ report evidence ↔ download); `queued` / `superseded` (report evidence ↔ format); `blocked` (run ↔ format) |
| **Consequence** | Code that “casts” or re-wraps a foreign enum (or raw shared string without axis context) silently lands in the wrong state family. Route outcomes can appear as fact-disclosure; process states can be rewritten across report/format/download axes. Undermines fail-closed separation of route vs disclosure. Existing unit test gives false confidence by only testing a non-overlapping route member. |
| **Smallest repair** | (1) Prefix values per family, e.g. `fact_not_publicly_disclosed` vs `route_not_publicly_disclosed`, **or** (2) custom `__new__`/`_missing_` that rejects `isinstance(value, Enum) and type(value) is not cls`, **and** (3) add tests for every known shared string + foreign-enum construction must raise. Prefer (1)+(3) if persisted strings must stay unambiguous on disk. |

### P1-1 — JSON Schema weaker than Pydantic on IANA timezone

| | |
|---|---|
| **Where** | `schemas/project-contract.schema.json` → `properties.timezone`; vs `ProjectContract._timezone_is_iana` / `create_project_contract` |
| **Reproducible input** | Instance with `"timezone": "Shanghai"` (and otherwise valid fields): Draft202012Validator against schema **accepts**; `create_project_contract(..., timezone="Shanghai", ...)` / model validate **rejects** |
| **Consequence** | Schema-only or external writers can persist non-IANA zones; later domain load fails or, if schema remains sole gate, cutoff localization is undefined |
| **Smallest repair** | Document known IANA check as runtime-only **and** add a non-empty pattern / `not` list for common mistakes is insufficient; keep Pydantic as gate **and** either embed `enum` of allowed zones used by product or add integration test that schema+domain reject the same fixtures; minimum: contract test that any schema-valid document must `ProjectContract.model_validate` (isomorphism suite), starting with `Shanghai`, `UTC+8`, `Asia/Shangha` |

### P1-2 — JSON Schema does not enforce HTML-first output order

| | |
|---|---|
| **Where** | Schema `outputs` uses `contains: {const: html}` + `uniqueItems`; model `_outputs_start_with_html_and_are_unique` requires `value[0] is OutputFormat.HTML` |
| **Reproducible input** | `"outputs": ["pdf", "html"]` — schema **valid**; `ProjectContract(..., outputs=(OutputFormat.PDF, OutputFormat.HTML), ...)` **invalid** |
| **Consequence** | Non-isomorphic interchange; order-sensitive consumers can disagree with schema-validated files |
| **Smallest repair** | Schema: `prefixItems` / first item `const: html` (2020-12), or `items` + explicit `prefixItems`; add contract test for `["pdf","html"]` rejected by both or accepted by both after canonical reorder-on-load |

### P1-3 — Offset requirement not enforced by schema

| | |
|---|---|
| **Where** | Schema `data_cutoff` / `created_at` `format: date-time` only; model `_datetimes_have_offsets` |
| **Reproducible input** | `"data_cutoff": "2026-08-11T23:59:59.999999"` (no offset) may pass format-tolerant schema validation; Pydantic rejects |
| **Consequence** | Ambiguous absolute instant for scientific cutoff if schema path is trusted alone |
| **Smallest repair** | Pattern requiring offset (`Z` or `±HH:MM`) on both datetime fields + isomorphism test |

### Non-blocking notes (not VETO alone)

- `stable_id` uses 24 hex of SHA-256: theoretical collision residual only.  
- Indication normalization is whitespace-only (no NFKC), unlike IDs — low risk for Task 1.1.  
- Tests do not assert P3–P5; coverage gap is part of P0-1.

## Final Verdict

**VETO**

Primary veto driver: **P0-1** cross-family `Enum` value coercion on shared strings (`not_publicly_disclosed`, `awaiting_user`, `queued`, `superseded`, `blocked`, …), which enables scientific/process state mix-write and is not covered by current unit tests. Secondary: **P1-1/P1-2/P1-3** Schema↔Pydantic non-isomorphism on IANA timezone, HTML-first outputs, and offset-bearing datetimes, despite package registration of the schema and solid factory/resume/refresh immutability on the Pydantic path.

Do not accept Task 1.1 until P0-1 is fixed and tested; close P1 isomorphism gaps before treating JSON Schema as an interchangeable contract surface. Codex retains final authority.
