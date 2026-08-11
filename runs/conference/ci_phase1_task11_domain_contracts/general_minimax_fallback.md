## Verification Report

### Command Results

| Command | Result |
|---|---|
| `pytest tests/unit/test_ids.py tests/unit/test_state_enums.py tests/contract/test_project_contract.py -v` | **4 passed in 0.05s** (all 4 Task 1.1 tests) |
| `pytest -q` (full regression) | **73 passed in 4.16s** |

### Adversarial Probe Results

**Probe 1 — `stable_id` acceptance:** None/0/False → `ValueError("稳定标识的身份材料必须是非空文本")`. NFKC fullwidth ("ＡＢＣ" == "ABC") ✓. Trim/collapse ✓. Kind & arg-count separators ✓. (Note: "ＡＢ\u3000Ｃ" differs from "ABC" because U+3000 collapses inside the same part but the test only asserts the *intra-part* separator; out-of-spec to require more.)

**Probe 2 — Cross-enum raw-value rejection:** 24 foreign-member/(shared raw value) pairs across the 9 state families — **all 24 raise `ValueError`** when constructed via the foreign Enum member. **0 silent accepts.**

**Probe 3 — Production validator rejection:** Both `project_contract_format_checker` (jsonschema) and `validate_project_contract_document` + Pydantic reject all 4 invalid fixtures: invalid IANA (`Shanghai`), HTML-not-first (`["pdf","html"]`), offsetless `data_cutoff` (`2026-08-11T23:59:59.999999`), offsetless `created_at`. `create_project_contract(timezone="Shanghai")` raises `ValueError("时区必须是有效的 IANA 时区")`.

**Probe 4 — Cutoff/DST/Resume/Refresh/Frozen:**
- EOD cutoff `2026-08-11T23:59:59.999999+08:00` ✓
- DST (America/New_York, 2026-03-08): cutoff carries `-04:00` post-spring-forward offset ✓
- Resume 24h later returns same frozen instance, `contract_version` unchanged, `data_cutoff` unchanged ✓
- Refresh emits new version `2` with same `project_id` and `+08:00` cutoff on `2026-08-12`; original v1 untouched ✓
- Refresh with earlier-or-equal cutoff → `ValueError("刷新后的数据截止日必须晚于当前合同")` ✓
- Mutation of frozen `ProjectContract.indication` blocked by Pydantic ✓

### Findings Table

| # | Probe | Result | Severity |
|---|---|---|---|
| 1 | `stable_id` rejects None/0/False | PASS | — |
| 2 | NFKC + whitespace collapse | PASS | — |
| 3 | Kind & arg-count separate deterministically | PASS | — |
| 4 | 24/24 cross-enum raw-value pairs rejected | PASS | — |
| 5 | Production checker & Pydantic reject 4 invalid fixtures | PASS | — |
| 6 | EOD cutoff + DST offset handling | PASS | — |
| 7 | Cross-day resume preserves version & cutoff | PASS | — |
| 8 | Refresh emits new version, freezes original | PASS | — |
| 9 | Frozen model blocks mutation | PASS | — |

### P0/P1 Defects

**None reproducible.** Every Task 1.1 invariant required by ADR 0004 holds against the live code under Python 3.13.13 / pytest 9.1.1, and full regression remains green (73/73).

### Final Verdict

**PASS**
