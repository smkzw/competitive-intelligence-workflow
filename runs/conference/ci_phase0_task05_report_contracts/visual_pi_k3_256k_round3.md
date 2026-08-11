# Conference Participant Output: ci_phase0_task05_report_contracts - visual_pi_k3_256k (Round 3)

## Boundary Check

- Read-only; no project file modified; report returned inline for runner persistence at `visual_pi_k3_256k_round3.md`.
- Scope held to the 11 listed files + test execution. Q-1 not reopened; no rendering/implementation work touched.

## Independent Work Product

### Test evidence (reproduced live this round, `.venv/bin/python` 3.13)

| Anchor | Round 2 | Round 3 | Result |
|---|---|---|---|
| 3 contract test files | 15 passed | **16 passed** (0.17s; +1 = `test_each_disposition_subpage_keeps_its_load_bearing_dimensions`) | PASS |
| Full regression `tests/` | 68 passed | **69 passed** (3.97s) | PASS |
| Ruff on 3 contract test files | clean | **All checks passed** | PASS |

### Closure table

| Item | Contract evidence (file → field) | Mechanical assertion | Verdict |
|---|---|---|---|
| D-1 | `page-catalogs/B.yaml` → `selection_rules.disposition_field_order` = "筛选与筛败、随机与接受治疗、完成治疗与完成研究、停止治疗与退出研究、失访、依从性、补救治疗、禁用药、方案偏离。" Matches §15.7 exactly: 筛选/筛败 first, 失访 before 依从性/补救/禁用/PD | `test_default_selection_rules…`: positional order assertion over 6 terms (`positions == sorted(positions)`) | CLOSED |
| D-2 | `page-catalogs/{A,B}.yaml` → `common_ae_rows` = "强制摘要行优先；其余依次按预定义特别关注不良事件与临床重要性、具有可比已报告值的产品数、最大绝对治疗—对照差、最高报告发生率和稳定术语标识选择默认显示行，不形成安全性排名。" Rates are deterministic ordering inputs; ranking explicitly excluded | Substring assertions for `最大绝对治疗—对照差`, `最高报告发生率`, `不形成安全性排名` × A/B | CLOSED |
| D-3 | `filter-contracts/common.yaml` → `evidence_drawer.profiles.baseline-observation` now includes `timepoint-window` （时间窗/基线时间定义， §15.5) | `test_baseline_and_disposition_drawers…` superset now includes `timepoint-window` | CLOSED |
| D-4 | `filter-contracts/B.yaml` → `profiles.b-plan-deviation` now includes `measurement-object` (PD 受试者数/事件数 separation, §13.7) | New `test_each_disposition_subpage_keeps_its_load_bearing_dimensions`: per-subpage required-dimension map covering all 7 disposition subpages | CLOSED |
| P2-① endpoint families simultaneous | `page-catalogs/{A,B}.yaml` → `endpoint_family` = "同时并列显示适用指导原则推荐…与核心竞品共同采用…；各终点族均完整保留。" | Substrings `同时并列显示`/`适用指导原则推荐`/`核心竞品共同采用` asserted | CLOSED |
| P2-② baseline order severity-first | `B.yaml` → `baseline_variable_order` = "疾病严重程度与关键判定指标、人口学、疾病背景、…" | `startswith("疾病严重程度与关键判定指标")` asserted | CLOSED |
| P2-③ HTML real visual check | `format-contracts/html.yaml` → `verification` adds "在合同视口逐页进行真实视觉检查" (§16.2) | Exact membership assertion | CLOSED |
| P2-④ PDF reader/print | `format-contracts/pdf.yaml` → `verification` adds "标准 PDF 阅读器可打开", "百分之百缩放与打印均可读" (§16.3) | Both asserted | CLOSED |
| P2-⑤ speaker view contents | `format-contracts/html-ppt.yaml` → `runtime.speaker_view_contents: [当前页, 下一页, 逐字稿, 计时器]` (§16.4) | Exact list equality assertion | CLOSED |
| P2-⑥ drawer pinning/reduced-motion | `filter-contracts/common.yaml` → `evidence_drawer.pin_multiple_items_for_side_by_side_review: true`, `reduced_motion_supported: true` (§15.5) | Both asserted `is True` | CLOSED |

### Newly discovered P0/P1 defects in Task 0.5 scope

None. Bounded check covered every changed field against its §12–16 source clause; all fixes are present in contract text **and** mechanically asserted. `A.yaml`'s `不适用` markers for baseline/disposition rules are correct (A owns no baseline/disposition page family).

### Final verdict: **PASS**

## Evidence And Assumptions

- Evidence: field texts quoted verbatim from current working tree; 16/69/ruff results executed this round, not transcribed.
- Assumption: closure interpreted per Codex's accepted-remediation wording (e.g., severity-first baseline ordering accepted as §15.7-conformant since 严重程度锚点 leads the first display group).
- Uncertainty: none remaining within Task 0.5 contract scope.

## Risks, Gaps, And Verification Needs

- Contract layer is now complete and fail-closed against §12–16; residual risk shifts to generator conformance in later phases (out of scope here).
- Selection-rule tests assert key substrings/order, not full-string equality — acceptable; further tightening optional, not required.

## Recommended Next Step

Codex closes Task 0.5 acceptance (16 contract tests + 69 regression + ruff green, D-1…D-4 and all six P2 items closed), records this round's evidence in the conference review, and proceeds to the next Phase-0 dependency per the plan's ordering. No further conference passes needed from this role for Task 0.5.
