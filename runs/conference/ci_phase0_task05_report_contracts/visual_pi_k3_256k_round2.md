All verification complete. Compiling the round-2 report.

# Conference Participant Output: ci_phase0_task05_report_contracts - visual_pi_k3_256k (Round 2)

## Boundary Check

- Read-only pass; no project file modified. Report returned inline; runner persists `visual_pi_k3_256k_round2.md`.
- Read set limited to the 15 Codex-listed files plus `git status`/`pytest`/`ruff` execution. Round-1 report (`runs/conference/.../visual_pi_k3_256k.md`) and Codex review are **outside** this round's read list, so the V-1…V-8 / R-x mapping below is **reconstructed** from the round-2 prompt's own enumeration and the observed field-level diffs. If Codex's numbering differs, the field-level findings stand regardless.
- Q-1 rejection acknowledged: `contracts/kangzhe/manifest.json` freeze supersedes §16.6 two-file wording; withdrawn, not re-audited.
- No other participant output viewed.

## Independent Work Product

### 1. Exact test evidence (reproduced this round, `.venv/bin/python`, Python 3.13)

| Anchor | Round 1 | Round 2 | Result |
|---|---|---|---|
| `pytest tests/contract/test_{page_catalogs,filter_contracts,format_contracts}.py` | 11 passed | **15 passed** (0.15s) | PASS |
| `pytest tests/` full regression | 64 passed | **68 passed** (3.73s) | PASS |
| `ruff check` on the 3 contract test files | pass | **All checks passed** | PASS |

New tests observed: `test_default_selection_rules_are_versioned_and_never_optimize_observed_results`, `test_a_and_b_bubble_charts_freeze_axis_direction_and_sample_size_radius`, `test_b_baseline_matrix_and_disposition_profiles_keep_required_user_dimensions`, `test_baseline_and_disposition_drawers_preserve_interpretation_fields`; `test_each_format_is_native_not_a_screenshot_or_cross_format_copy` extended with PDF/HTML-PPT assertions.

### 2. V-1…V-8 closure table (mapping reconstructed; see Boundary Check)

| # | Item (reconstructed) | Contract field(s) now present | Mechanically asserted? | Verdict |
|---|---|---|---|---|
| V-1 | B baseline child profiles | `filter-contracts/B.yaml` `profiles.b-baseline*` now include `target-mechanism, region, variable-domain` (11 dims each) | YES — `test_b_baseline_matrix_and_disposition_profiles_keep_required_user_dimensions` asserts 9-dim `REQUIRED_B_BASELINE ⊆` each of 4 profiles | CLOSED |
| V-2 | B matrix profile | `b-matrix` now includes `analysis-population, ae-term-grade, denominator-role` | YES — same test asserts the 3 ⊆ `b-matrix` | CLOSED |
| V-3 | Eight disposition profiles | All 8 `b-*disposition-family` profiles now carry `target-mechanism` + `analysis-population`/`disposition-population`; `b-screen-failure` correctly omits `cohort-arm`/`period` （筛败以筛选人群为语境， §13.7) | YES — test asserts `target-mechanism` in all 8; **but see D-4: per-profile depth assertion is shallow** | CLOSED with residual |
| V-4 | Evidence drawer profiles | `common.yaml` drawer `fields` +4 (`canonical-field-family, statistic-form-or-measurement-object, reason-original-canonical, reason-mutual-exclusivity`); `baseline-observation`/`trial-disposition` profiles updated | YES — `test_baseline_and_disposition_drawers_preserve_interpretation_fields` | CLOSED with residual (D-3) |
| V-5 | Deterministic selection rules (§15.7) | `selection_rules` block in A/B/C catalogs, `version: "1.0"`, anchor rule carries "不使用疗效或安全性数值偏好" | PARTIAL — test asserts key presence + one substring only; **content not validated against §15.7 (see D-1, D-2)** | CLOSED structurally; content defects D-1/D-2 |
| V-6 | C candidate-path rule (§14.3) | `C.yaml selection_rules.minimum_candidate_design_paths: 2`, `unique_best_design_allowed: false` | YES — exact value assertions | CLOSED (note: §14.3's "或明确说明缺少背景" escape clause not modeled; current form is stricter/fail-closed, acceptable) |
| V-7 | Bubble direction/radius (§12.4/§13.5) | `bubble_chart_contract` in A + B: `y_axis` 倒序， exact annotation "向上 = 发生率更低 = 观察到的安全性位置更有利", `x_axis_direction`, `radius_formula: "r = k × sqrt(N/pi)"`, `no_pooling`, `no_composite_score` | YES — 6 exact assertions × A/B | CLOSED |
| V-8 | PDF orientation/bookmarks; HTML-PPT viewports/page numbers | `pdf.yaml`: `landscape_auto_switch: [宽表, 森林图, 纵向多系列, 设计时间线, 终点矩阵]`, `orientation_change_only_at_page_boundary`, `bookmarks_required`; `html-ppt.yaml`: `visual_acceptance_viewports: [1280×720, 1920×1080, 2048×1024, 用户实际最大化窗口]`, `page_number_excluded_page_types: [封面, 目录, 章节首页, 结束页]` | YES — exact list equality assertions | CLOSED |

R-1/R-3/R-4 (mapping uncertain): observable additions consistent with them — `html.yaml verification` expanded （链接与目录跳转、控制台无错误、溢出/遮挡、键盘导航与证据查看）, `pdf.yaml verification` +书签与页码正确， `html-ppt.yaml verification` +页码页型， plus the four new tests above. All present and passing.

### 3. Newly discovered P0/P1 defects (Task 0.5 scope)

No P0. Four P1 items, two are frozen contract text that **contradicts** the design spec (worse than omission — a conforming generator would deterministically violate the spec):

- **D-1 (P1)** — `docs/architecture/page-catalogs/B.yaml` → `selection_rules.disposition_field_order` = "随机、治疗、完成、退出、依从性、失访、筛败、退出原因、补救治疗、禁用药、方案偏离"。§15.7 mandates fixed order: 先显示**筛选/筛败**、随机/治疗、完成治疗/研究、停止治疗/退出研究和**失访**，**再**显示依从性、补救治疗、禁用药及 PD。Contract drops 筛选， puts 筛败 7th, and puts 依从性 before 失访. Smallest fix: replace the string with "筛选/筛败、随机/接受治疗、完成治疗/完成研究、停止治疗/退出研究、失访、依从性、补救治疗、禁用药、方案偏离（PD)"; extend the selection-rules test to assert 筛败 precedes 依从性/补救/禁用/PD.
- **D-2 (P1)** — `docs/architecture/page-catalogs/B.yaml` (and mirrored in `A.yaml`) → `selection_rules.common_ae_rows` = "…不因发生率高低筛选。" §13.4 mandates rate-based union criteria （任一治疗组 ≥5%、治疗—对照绝对差 ≥5pp、来源高频） and §15.7 mandates 强制摘要行优先 + ordered tiebreaks （可比产品数、最大绝对差、最高报告发生率、稳定术语 ID)。"不因发生率高低筛选" contradicts both. Smallest fix: rewrite as "强制摘要行优先；其余依次按预定义 AESI/临床重要性、具有可比已报告值的产品数、最大绝对治疗—对照差、最高报告发生率和稳定术语标识选择默认显示行，不形成安全性排名"; assert the substring "不形成安全性排名" (currently absent from both rule and test).
- **D-3 (P1)** — `docs/architecture/filter-contracts/common.yaml` → `evidence_drawer.profiles.baseline-observation` lacks `timepoint-window`. §15.5: baseline_observation 抽屉必须显示"时间窗或基线时间定义"。Round-2 fix added 字段族/统计形式 but dropped the time dimension; the field exists in the generic `fields` list, only the profile omits it. Smallest fix: add `timepoint-window` to the `baseline-observation` profile and to the superset assertion in `test_baseline_and_disposition_drawers_preserve_interpretation_fields`.
- **D-4 (P1)** — `docs/architecture/filter-contracts/B.yaml` → `profiles.b-plan-deviation` lacks `measurement-object`. §13.7 forbids interchanging PD 受试者数/事件数 and lists 计量对象 as a required multi-select dimension for the disposition family; the dedicated PD page is precisely where that filter is load-bearing (b-adherence has it; b-plan-deviation does not). Smallest fix: add `measurement-object` to `b-plan-deviation`; strengthen the disposition-profile test from `target-mechanism`-only to a per-profile required-dimension map.

P2 notes (non-blocking, recorded for Codex): ① `common_ae_rows`/`endpoint_family` wording makes competitor-adopted endpoint families a fallback ("若不唯一，则采用") where §13.3 requires simultaneous display; ② `baseline_variable_order` puts 严重程度 third while §15.7 puts GateSpec 严重程度锚点 in the first display group; ③ `html.yaml verification` lacks an explicit 真实视觉检查 item (§16.2); ④ `pdf.yaml verification` lacks 标准阅读器可打开/100% 打印可读 (§16.3); ⑤ HTML-PPT speaker-view contents （当前页/下一页/逐字稿/计时器） not enumerated, only key `S` and note length; ⑥ drawer 证据固定并列 (pinning) and 减少动态效果 not machine-expressed anywhere.

### 4. Final verdict: **VETO**

Structure is now complete and 15/15 contract tests + 68/68 regression pass with real assertions; this is no longer a shell. But D-1 and D-2 are machine-frozen deterministic-default rules that affirmatively contradict §15.7/§13.4 — they decide what a Chinese clinical medical manager sees first on the safety heatmap and disposition pages, and no current test would catch the drift (selection-rules test asserts presence, not content). D-3/D-4 are normative §15.5/§13.7 field omissions with one-line fixes. All four fixes are small and local; re-running the three contract test files after the edits is sufficient re-verification.

## Evidence And Assumptions

- **Evidence**: file contents quoted above were re-read this round post-edit; test/ruff outputs reproduced live (`15 passed`, `68 passed`, ruff clean). Round-1 anchors (11/64) confirmed from round-1 transcript.
- **Inference**: V/R numbering reconstruction (Boundary Check); the assumption that round-1 V-5/V-7/V-8 correspond to selection_rules/bubble/format-runtime fixes is strongly supported by the round-2 prompt's own attention list but not byte-verified against my round-1 report.
- **Uncertainty**: R-1/R-3/R-4 exact identities; whether D-1/D-2 wording was an intentional Codex simplification (if so, the design spec, not the contract, is being relaxed — that requires user-visible spec amendment per project rule "do not silently relax").

## Risks, Gaps, And Verification Needs

- Selection-rules tests validate existence, not §15.7-conformant content — same class of drift can recur silently. Recommend content assertions for all five rule strings.
- Per-profile disposition assertions check one dimension only; D-4-type omissions recur without a required-dimension map per profile.
- Remaining unverified-by-me: actual rendering/generation (out of Task 0.5 scope; later phases), and any Codex-side rationale for D-1/D-2 wording.

## Recommended Next Step

Codex applies the four minimal fixes (D-1: rewrite one string + one order assertion; D-2: rewrite two strings + ranking-absence assertion; D-3: one list entry + test superset; D-4: one list entry + per-profile dimension map), reruns the three contract test files, and returns for a short round-3 closure check limited to those four fields. After that I expect PASS. Bounded question for Codex: were the D-1/D-2 wordings deliberate simplifications of §15.7/§13.4? If yes, the design spec needs an explicit amendment decision recorded; if no, the fixes above restore conformance.
