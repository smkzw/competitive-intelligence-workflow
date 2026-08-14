# Execution Output: ci_phase5_task51_execution - worker_01

## Boundary And Context Check

- Read set consumed: `AGENTS.md`, `context/ci_phase5_task51_execution_execution_context.md`, `plans/codex_execution_ci_phase5_task51_execution.md`, plus authorized sources of truth: `context/ci_phase5_task51_context.md`, spec §2/§3.2/§12.1–12.2 (`docs/specs/competitive-intelligence-workflow-design-v1.2.md`), Hermes plan Task 5.1 (`../.hermes/plans/2026-08-10_160047-…md`), `policies/ontology/innovation-therapy-v1.yaml`.
- Confirmed Phase 3 accepted contracts to build on, not duplicate: `gates/models.py` (`DevelopmentMaturity`, `ClinicalResultState`, `SourceRole`, `derive_result_bearing`), `gates/evaluator.py` (`derive_product_maturity`, `check_result_bearing`, predicates `maturity_ge_clinical`/`maturity_ge_submission`/`result_bearing`), Phase 4 `reports/common/evidence_view.py` (`EvidenceField` value-XOR-state presence model).
- Wrote only authorized paths: `src/ci_workflow/reports/a/{contracts,analysis,__init__}.py`, `tests/reports/a/test_maturity_gate.py`. No production writes, no package installs, no report/HTML/PDF generation, no external accounts.

## Work Performed

TDD RED→GREEN for assigned item: 先写成熟度递增字段失败测试，再实现 A 项目合同与逐层必需字段判定。

1. **RED**: wrote `tests/reports/a/test_maturity_gate.py` (27 tests). First run failed at collection: `ModuleNotFoundError: No module named 'ci_workflow.reports.a'`.
2. **contracts.py** — A 项目合同与成熟度递增字段规格:
   - `MaturityLevel` (ALL_PROJECTS < CLINICAL < FILING_APPROVAL_TERMINATION < RESULT_BEARING) with monotonic rank.
   - `RequiredFieldKey` closed set (17 keys across 4 layers per §12.2 table) + `REQUIRED_FIELD_SPECS` (label_zh/description_zh/allows_not_applicable) + `required_fields_for()` + `assert_ladder_monotonic()`.
   - NA-allowance matrix: only 中国/境外阶段状态日期 and 当前开发者/原研方 allow explicit 不适用; all other fields reject NA.
   - Record types: `CoreTrialRecord` (身份/角色/状态), `RegulatoryEventRecord` (事件/地域/日期), `AnchorTrialRecord` (trial_id + evidence bindings), `EfficacyRecord` (§12.2 全成分: 原始定义、方向、单位、时间点、分析人群、治疗组、适用时对照组与分母), `SafetySummaryRecord` (summary_kind TEAE/SAE/AESI/其他、事件定义、时间窗、组别、分母、披露状态).
   - `AProjectContract`: frozen, extra=forbid; construction rejects blank/whitespace text, non-`included` eligibility, and inconsistent `result_bearing`↔`result_bearing_basis_ids` (no empty claim, no downgrade).
3. **analysis.py** — 逐层必需字段判定:
   - `determine_maturity_level(project)` — pure derivation from accepted `DevelopmentMaturity` + `result_bearing` verdicts; no override/downgrade parameters.
   - `evaluate_maturity_gate(project)` — evaluates union of layers ≤ maturity; per-field `FieldOutcome` (satisfied / explicit NA / missing) with native-Chinese clinical reasons (尚未公开/穷尽检索后未找到/技术暂不可用 are distinct missing states); `MaturityGateResult.blocked` fail-closed on any missing; `missing_keys`/`missing_fields` for worker_03 aggregation.
   - L4 minimums: ANCHOR_TRIAL (≥1 evidence-bound anchor), CORE_EFFICACY_RECORD (≥1 record with value-bearing disclosure + complete slots), SAFETY_SUMMARY_RECORD (≥1 record of kind TEAE/SAE with value-bearing disclosure); "Results posted flag but incomplete values" → blocked (recovery layer), AESI-only rows do not satisfy the TEAE/SAE minimum.
4. **GREEN**: 27/27 pass. Repo-wide: ruff clean, strict mypy clean (87 files), 786 tests green (reports/unit/contract/graph/migration 548 + integration 211 + new 27).

## Artifacts And Evidence

| File | Lines | Role |
|---|---|---|
| `src/ci_workflow/reports/a/contracts.py` | 462 | A 项目合同、成熟度分层、17 字段规格、记录类型 |
| `src/ci_workflow/reports/a/analysis.py` | 426 | 成熟度推导与逐层必需字段判定、中文阻断原因 |
| `src/ci_workflow/reports/a/__init__.py` | 86 | 包导出 |
| `tests/reports/a/test_maturity_gate.py` | 565 | 27 个失败测试（现全绿） |

Test coverage highlights: L1 字段各自独立阻断（未公开/检索后未找到）；区域阶段/状态/日期齐备或整组显式不适用；不允许不适用冒充（靶点/机制）；临床项目缺核心试验三重字段阻断、临床前项目不因无试验失败；申报层缺事件/地域/日期阻断；终止项目保持申报层不放行；result_bearing 项目缺锚定/疗效/安全摘要阻断；flag-only 不完整值进入恢复层；AESI-only 不满足 TEAE/SAE 最低记录；结果承载与已批准项目不可降级跳过上层；评估接口仅 project 参数（无跳过/删除/降级出口）；评估确定性与身份/顺序稳定；阻断原因含中文医学语言。

## Commands And Observations

- `uv run pytest tests/reports/a/test_maturity_gate.py -q` — RED: 1 collection error (`ModuleNotFoundError`); GREEN: `27 passed in 0.09s`.
- `uv run ruff check src tests` — `All checks passed!`
- `uv run mypy src` — `Success: no issues found in 87 source files`
- `uv run pytest tests/reports tests/unit tests/contract tests/graph tests/migration -q` — `548 passed in 27.56s`
- `uv run pytest tests/integration -q` — `211 passed in 25.41s`
- Browser/acceptance suites (`tests/browser`, `tests/acceptance`) not run by worker (require live Playwright browsers; final visual/rendered acceptance is Codex's authority).

## Blockers Or Missing Environment

None. All tools and environments present; no package installation needed.

## Rerun Requests Or Next Step

- Next: worker_02 — result-bearing 确定性触发及疗效/TEAE-SAE 缺失阻断 on the same files; `AProjectContract.result_bearing`/`result_bearing_basis_ids` and the L4 record types are the stable contract to fill from evidence. worker_03 — 整批分析与中文阻断说明 can aggregate `MaturityGateResult` per `project_id` (blocked/missing_fields/maturity_level) without any Top-N or deletion; evaluation is a pure function of frozen contracts.
- Contract stability guarantee: both later workers must keep the 27 tests green (后序改动保留前序已通过合同); my `_evaluate_key` dispatch covers the full 17-key ladder — new *functions* are additive, new ladder *keys* would require extending the dispatch.
- Remaining for Codex: final acceptance of the three test files, full-suite browser run, and review that no 成熟项目降级/删除/Top-N false-green exists.
