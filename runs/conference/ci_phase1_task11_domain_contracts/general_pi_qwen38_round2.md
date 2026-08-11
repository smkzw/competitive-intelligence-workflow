All verifications complete. Here is my round-2 closure report.

---

# Conference Participant Output: ci_phase1_task11_domain_contracts - general_pi_qwen38 (round 2)

## Boundary Check

- Worked only inside the project root; read only the six allowed files plus the design spec and ADR already loaded in round 1.
- No files modified. No runner report path written with tools.
- No other participant output consulted.

## Independent Work Product

### Remediation audit — code diff vs round 1

| Item | Round 1 state | Round 2 state | Verdict |
|---|---|---|---|
| `ids._normalize_identity_part` param type | `object` → `str(value)` swallowed `None`/`0`/`False` into `"None"`/`"0"`/`"False"` | `value: str` + `isinstance` guard raises `ValueError("…必须是非空文本")` before any conversion | **Closed** |
| `stable_id` signature | `*identity_parts: object` | `*identity_parts: str` | tightened; consistent |
| Schema `timezone` | `{"type":"string","minLength":1}` (accepted `"Shanghai"`) | `{"type":"string","format":"iana-timezone","minLength":1}` | **Closed** |
| Schema offset enforcement | `format: date-time` only (naive datetimes accepted) | added `pattern: "(?:Z|[+-][0-9]{2}:[0-9]{2})$"` on both `data_cutoff` and `created_at` | **Closed** |
| Schema HTML-first | `contains: {const: html}` only (allowed `["pdf","html"]`) | added `prefixItems: [{"const":"html"}]` | **Closed** |
| Test `test_ids` | whitespace + empty-string only | added NFKC (`ＡＢＣ`→`ABC`), separator non-commutativity, `None`/`0`/`False` probes | covers VETO-1 |
| Test `test_state_enums` | `!=` (value inequality, would pass even on broken identity) + 4 foreign probes | `type(...) is not ...` (true identity) + 6 foreign shared-value pairs | strengthens OBSERVATION |
| Test `test_project_contract` | schema check only on valid contract | added `_project_contract_validator` with IANA format checker; 4 invalid payloads asserted to fail **both** schema and Pydantic | covers OBSERVATION-1 parity |
| DST probe | absent | `America/New_York` 2026-03-08 → `-04:00` (DST began 2026-03-08 02:00) | confirms offset materialization, not a hardcoded `+08:00` |

### Executed tests

| Suite | Command | Result |
|---|---|---|
| Task 1.1 (4 tests) | `uv run python -m pytest tests/unit/test_ids.py tests/unit/test_state_enums.py tests/contract/test_project_contract.py -v` | **4 passed** in 0.06s |
| Full regression | `uv run python -m pytest` | **73 passed** in 3.94s |
| Runtime | Python 3.13.13, pytest 9.1.1, `.venv` | matches Phase 0 lock |

### Independent adversarial probes (mine, not the suite's)

**VETO-1 closure — non-str rejection before string conversion:**

| Input | Observed |
|---|---|
| `stable_id("product", None)` | `ValueError('稳定标识的身份材料必须是非空文本')` |
| `stable_id("product", 0)` | `ValueError('稳定标识的身份材料必须是非空文本')` |
| `stable_id("product", False)` | `ValueError('稳定标识的身份材料必须是非空文本')` |
| `stable_id("product", True)` | `ValueError(...)` |
| `stable_id("product", 5)` | `ValueError(...)` |
| `stable_id(None, "x")` (kind) | `ValueError(...)` |

No path reaches `str(value)` for non-str. The round-1 collision (`stable_id("product", 0)` == `stable_id("product", False)` == `stable_id("product", "0")` distinct from `stable_id("product", "False")`) is eliminated: `None`/`0`/`False`/`True`/int all rejected before normalization. Separator non-commutativity (`("ab","c") != ("a","bc")`) still holds — no regression.

**OBSERVATION-1 closure — schema/Pydantic rejection parity:**

| Probe payload | JSON Schema | Pydantic |
|---|---|---|
| `timezone: "Shanghai"` (non-IANA) | reject | reject |
| `timezone: "localtime"` (non-IANA) | reject | reject |
| `outputs: ["pdf","html"]` (HTML not first) | reject | reject |
| `outputs: ["pdf"]` (no HTML) | reject | reject |
| `data_cutoff` without offset | reject | reject |
| `created_at` without offset | reject | reject |
| extra field `rogue: 1` | reject (`additionalProperties: false`) | reject (`extra="forbid"`) |
| `schema_version: "2.0"` | reject (`const: "1.0"`) | reject (`Literal["1.0"]`) |

Full parity: no field where one layer accepts and the other rejects. The IANA format checker (`is_iana_timezone` via `ZoneInfo`) is wired into the test's `_project_contract_validator`; the schema itself declares `format: iana-timezone` so any compliant validator with a format checker enforces it.

**Shared-value foreign-enum probes (8 pairs):**

| Target | Foreign member (shared `value`) | Observed |
|---|---|---|
| `FactDisclosureState` | `RouteAttemptResult.NOT_PUBLICLY_DISCLOSED` | rejected |
| `ReportEvidenceState` | `ProjectRunState.AWAITING_USER` | rejected |
| `DownloadRequestState` | `ProjectRunState.AWAITING_USER` | rejected |
| `FormatArtifactState` | `ReportEvidenceState.QUEUED` | rejected |
| `FormatArtifactState` | `ReportEvidenceState.SUPERSEDED` | rejected |
| `FormatArtifactState` | `ProjectRunState.BLOCKED` | rejected |
| `ReportEvidenceState` | `DownloadRequestState.AWAITING_USER` | rejected |
| `FactReviewState` | `FormatArtifactState.SUPERSEDED` | rejected |

Python `Enum` semantics make this the expected behavior (value+type must match), but the probes confirm it holds at runtime — a foreign enum member is never silently coerced into another family. Same-enum lookup still works (`ReportEvidenceState.QUEUED == ReportEvidenceState(ReportEvidenceState.QUEUED)`). The `type(...) is not ...` test assertion is now a true identity check, not a value comparison.

**Immutability invariant:**

| Check | Observed |
|---|---|
| `model_config.extra` | `forbid` |
| `model_config.frozen` | `True` |
| `c.contract_version = 999` | `ValidationError` (frozen blocks mutation) |
| Extra field at construction | `ValidationError` |

`ProjectContract` is genuinely immutable and closed to extra fields — the "historical snapshot not drifting" and "scientific state not mixed" objectives hold: a frozen contract cannot be mutated in place, and resume returns the same object (`resumed is contract`).

## Evidence And Assumptions

**Directly observed (no inference):**
- All file contents as read above.
- 4/4 Task 1.1 tests pass; 73/73 full suite passes (Python 3.13.13).
- All 6 non-str `stable_id` rejections raise `ValueError` with the `非空文本` message.
- All 8 schema/Pydantic parity probes reject on both layers.
- All 8 foreign-enum probes reject.
- `ProjectContract` is `frozen=True, extra="forbid"`; mutation and extra-field both raise `ValidationError`.
- DST probe: `America/New_York`, 2026-03-08 → `2026-03-08T23:59:59.999999-04:00`. US DST 2026 began 2026-03-08 02:00 local, so the `-04:00` offset is correct for end-of-day — confirms offset is materialized from the zone, not hardcoded.

**Assumptions:**
- The `.venv` managed by `uv` is the project's authoritative test environment (Python 3.13.13, matching the `>=3.12,<3.14` manifest).
- `contracts.py` was not in the round-2 allowed read list; I relied on the round-1 read for the resume/refresh/cutoff logic. The test file exercises those paths and passes, and the round-1 analysis of that logic found no defect. If Codex wants a fresh line-by-line re-read of `contracts.py`, that file should be added to the read list.

## Risks, Gaps, And Verification Needs

**No blocking defect found.** Round-1 VETO-1 and OBSERVATION-1 are both closed with evidence. Remaining non-blocking observations:

1. **`stable_id` type hint vs runtime (cosmetic, P3):** The signature is `stable_id(kind: str, *identity_parts: str)`, but `kind` is also run through `_normalize_identity_part` which now enforces `isinstance(value, str)`. This is correct and consistent. No action needed; noting for completeness.

2. **Schema IANA enforcement depends on a format checker (P3, pre-existing):** The schema declares `format: iana-timezone`, but `jsonschema` only enforces `format` when a `FormatChecker` is provided. The test wires one in; any downstream validator that omits `FormatChecker` would accept `"Shanghai"`. This is standard JSON Schema behavior, not a defect, but Codex should ensure the production validator path (Task 1.2+ SQLite/persistence) registers a `FormatChecker` — otherwise the schema's IANA guard becomes advisory. **Bounded question for Codex:** will the persistence layer (Task 1.2) construct its contract validator with a `FormatChecker`, or should `contracts.py` expose a shared validator factory to guarantee the IANA check is never skipped?

3. **`_local_date` datetime-with-zone path (P3, not in allowed read set):** In round 1 I noted `_local_date` converts a zone-aware datetime cutoff via `astimezone(timezone).date()`, which is correct. The DST probe confirms end-of-day offset materialization. No defect.

4. **No cross-day resume drift test for a different timezone (P3):** The resume test uses `Asia/Shanghai` (no DST). The DST probe covers `America/New_York` cutoff materialization but not a cross-day *resume* in a DST-transitioning zone. The resume function returns the contract unchanged (`resumed is contract`), so drift is structurally impossible, but a DST-zone resume assertion would make the invariant explicit. Non-blocking — the `is` identity check already proves no recompute.

## Recommended Next Step

**Final verdict: PASS.**

| Round-1 finding | Status | Evidence |
|---|---|---|
| VETO-1: `stable_id` accepted `None`/`0`/`False` via `str()` coercion → distinct objects could collide | **Closed** | `_normalize_identity_part` now `isinstance`-guards and raises `ValueError` before conversion; 6 independent probes reject; test covers `None`/`0`/`False` |
| OBSERVATION-1: schema accepted non-IANA tz, HTML-not-first, offset-less datetimes; Pydantic/schema parity unverified | **Closed** | Schema now has `format: iana-timezone`, offset `pattern`, `prefixItems` HTML-first; 8 parity probes reject on both layers; test asserts both |

All nine state families match v1.2 §8.4/§10.2 exactly; cross-enum identity is enforced; the project contract is frozen, IANA-validated, offset-validated, HTML-first, and A/B/C-multi-select; cutoff materializes at creation-day end in the declared timezone; resume returns the same object (no drift); refresh creates a new version (no rewrite). 4/4 target tests and 73/73 full regression pass on Python 3.13.13.

No further remediation required for Task 1.1 scope. The two P3 observations (format-checker registration in the persistence layer; DST-zone resume assertion) are forward-looking notes for Task 1.2+, not Task 1.1 blockers.
