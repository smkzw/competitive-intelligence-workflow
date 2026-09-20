Now I have enough material to render the targeted follow-up verdict. Let me check whether the `g_format_quality_check_passed` guard's full `required_true` list (29 booleans) is actually seven per-domain checks rather than seven domain-specific evidence records, and check whether `_validate_run` for the `verification_reference` enforces per-domain evidence refs.

Looking at the schema and verifier already read:
- `g_format_quality_check_passed` requires 29 `required_true` flags; among them seven are explicitly `visual_copy_check_passed`/`visual_hierarchy_check_passed`/`visual_layout_check_passed`/`visual_color_check_passed`/`visual_chart_table_check_passed`/`visual_interaction_check_passed`/`visual_format_render_check_passed` — these are the seven per-domain pass markers, not standalone booleans.
- `validate_visual_verification_reference` requires `domains` array with exactly 7 items covering all7 domains, each with `criteria` (≥1, unique, ≥8 chars) + `evidence_refs` (≥1, unique); `verdict=accepted` requires every domain `status==accepted`; `producer_identity != verifier_identity`.
- `validate_visual_render_evidence` enforces: `metrics` all-zero (no overflow/clip/labels), `unavailable_required_fields` must each have a `responsive_alternatives[*].verified=true` entry, `visible_text_scan.passed=true` with both token lists empty, `defects[].blocking+open` empty, `format=html` requires Chromium+WebKit AND {768,1024,1440} AND `interaction_checks` for {page_load, filter_change, drill_down, search, keyboard, reduced_motion}.
- `renderTarget.screenshot_sha256` and `candidate_artifact_digest` and `visual_plan_digest` are SHA-256 pattern-bounded; the verifier takes `expected_artifact_digest/expected_plan_digest` parameters to prevent digest drift between layers.
- `_validate_acceptance_matrix` blocks the "七个笼统布尔" attack: `generic = {"通过当前格式专属检查", "符合设计规范", "视觉效果良好", "检查通过"}` — any criterion equal to one of these rejects the plan.
- `visual-package-qc/SKILL.md` and `visual-design-director/SKILL.md` already define three-role isolation and forbid producer self-signing / old summary reuse.
- Existing negative tests cover: WebKit/1024 missing, failed interaction, label overlap, open blocker, text-scan failure, hidden-field-without-alternative, candidate-digest drift, self-sign, render-digest drift, accepted-summary-with-rejected-domain, render-only shortcut, non-boolean acceptance shortcuts (e.g., string `"yes"` instead of bool), wrong family/object scope, plan/snapshot/format drift on queued+candidate guards, beautification rounds {0,4}, self-signed verdict, round=0, blocking with limit vs non-visual, verdict-digest drift, queued→delivery_ready jump, missing render-evidence in graph.

I have enough material. Writing the follow-up verdict now.

---

# 独立视觉审阅（复核）：MiniMax

## 结论

**PASS**

## 复核针对的假通过与机制堵口

| 假通过攻击 | 合同/守卫字段（定位） | 触发条件 |
|---|---|---|
| 只有文件或截图存在 | `visual-render-evidence.schema.json` `renderTargets[*].metrics.{horizontal_overflow_px,clipped_text_count,label_overlap_count,unreadable_label_count}` 全部必须为 0；`defects[].blocking=true&status=open` 必须为空 | `visual_finalization.py:364-391` |
| 只有无横向滚动 | `metrics.label_overlap_count`、`clipped_text_count`、`unreadable_label_count` 与 `visible_text_scan` 独立校验；非布尔写法被 `guard_not_satisfied` 拒 | `visual_finalization.py:362-384`、`guards.py:170-181`（非布尔短路） |
| 隐藏字段无入口 | `renderTargets[*].unavailable_required_fields` 中每项必须有同字段 `responsive_alternatives[*].verified=true` | `visual_finalization.py:368-377`、`test_hidden_required_field_requires_a_verified_user_visible_alternative` |
| 图表标签碰撞 | `metrics.label_overlap_count=0`、`metrics.unreadable_label_count=0`、`defect.severity/blocking` 必须全关 | `visual-render-evidence.schema.json:54-60`、`test_visual_render_evidence_rejects_incomplete_or_unreadable_output(label_overlap)` |
| 工程化 / 未中文化文字 | `visibleTextScan.{passed=true, engineering_tokens_found=[], untranslated_tokens_found=[]}` | `visual_finalization.py:378-384`、`test_visual_render_evidence_rejects_incomplete_or_unreadable_output(text_scan)`、`test_frozen_a_portal_pages_are_chinese_and_pipeline_free` |
| 生成者自签 |策划书 `validate_visual_verification_reference`: `_require(producer_identity != verifier_identity)`；守卫 `distinct_fields=(("producer_identity","verifier_identity"))` | `visual_finalization.py:433`、`guards.py:580`、`test_independent_visual_verdict_rejects_self_signing`、`test_format_acceptance_rejects_self_signed_visual_verdict` |
| 旧摘要给新候选背书 | `render_evidence.candidate_artifact_digest == visual_plan_digest` 与 `expected_artifact_digest/expected_plan_digest/expected_render_digest` 三层绑定；`visual_verdict_*` 四向绑定到 candidate/render/plan/format；`visual_verdict_render_digest==render_evidence_digest` | `visual_finalization.py:349-358, 432-441`、`guards.py:558-578`、`test_visual_render_evidence_rejects_candidate_digest_drift`、`test_independent_visual_verdict_rejects_digest_drift`、`test_format_acceptance_rejects_visual_verdict_digest_drift` |
| 七个笼统布尔代替逐域审阅 | 策划书 `_validate_acceptance_matrix` 黑名单 `{通过当前格式专属检查, 符合设计规范, 视觉效果良好, 检查通过}`；独立 verdict `domains` 数组长度锁定为 7 且必须等于 `ACCEPTANCE_DOMAINS`，每项 `criteria.minItems=1`/`uniqueItems`/`minLength=8`、`evidence_refs.minItems=1`/`uniqueItems`；verdict=accepted 要求每域 status==accepted | `visual_finalization.py:289-295, 442-452`、`schemas/visual-verification-reference.schema.json:33-37`、`test_visual_plan_rejects_generic_acceptance_language`、`test_independent_visual_verdict_rejects_accepted_summary_with_rejected_domain` |
| 只有真实渲染但跳过策划书 | 守卫 `g_format_queued_generating.required_true` 含 `visual_plan_bound`+`visual_plan_snapshot_matches`+`visual_plan_format_matches`+`visual_plan_design_contract_matches`，缺失任一被拒 | `guards.py:391-396`、`test_format_generation_rejects_plan_binding_drift` |
| 跳到 delivery_ready | 状态机未声明该边，直接 `undeclared_transition`；即便绕过，守卫仍要求 `visual_verdict_id` 存在 | `tests/graph/test_visual_finalization_graph_negative.py:368-384,325-339` |
| 美化回环越界 | `g_format_quality_check_generating`/`g_format_quality_check_passed` 均带 `min_int_fields=(("beautification_round",1))`+`max_int_fields=(("beautification_round",3))` | `guards.py:492-493, 581-582`、`test_format_beautification_loop_rejects_rounds_outside_one_to_three`、`test_format_acceptance_rejects_zero_beautification_round` |
| HTML 仅单一引擎或缺宽度 | `format=html` 时强制 `{"chromium","webkit"}.issubset(engines)` 与 `{768,1024,1440}.issubset(widths)` | `visual_finalization.py:393-401`、`test_visual_render_evidence_rejects_incomplete_or_unreadable_output(missing_webkit, missing_1024)` |
|缺失六类 HTML 交互 | `format=html` 时 `interaction_checks` 必须覆盖 `{page_load, filter_change, drill_down, search, keyboard, reduced_motion}` 且 `passed=true` | `visual_finalization.py:402-413`、`test_visual_render_evidence_rejects_incomplete_or_unreadable_output(failed_interaction)` |

## 关键合同/守卫定位

- `schemas/visual-render-evidence.schema.json:30-107`（`renderTarget` / `responsiveAlternative` / `interactionCheck` / `visibleTextScan` / `defect` 五类硬约束）
- `schemas/visual-verification-reference.schema.json:23-39`（`domains` 长度锁定 7、`domain.enum` 与 `ACCEPTANCE_DOMAINS` 对齐）
- `src/ci_workflow/graph/visual_finalization.py:334-453`（`validate_visual_render_evidence`、`validate_visual_verification_reference`）
- `src/ci_workflow/graph/visual_finalization.py:265-274`（HTML 交互状态必填触发器）、`289-295`（验收矩阵黑名单）
- `src/ci_workflow/graph/guards.py:499-587`（`g_format_quality_check_passed` 七域逐域 `required_true` + 三向摘要绑定 + `distinct_fields` + 三轮上下界）
- `src/ci_workflow/graph/guards.py:389-449,588-610`（queued/candidate/passed→delivery_ready 三段摘要与字段绑定）
- `tests/contract/test_visual_render_evidence.py` 与 `tests/graph/test_visual_finalization_graph_negative.py` 已覆盖上述每一类假通过

## 非阻断观察（不构成 FAIL）

1. `g_format_quality_check_passed` 共 29 个 `required_true` 旗标，七域逐域旗标已显式存在；当前负例测试只校验"非布尔写法短路"，未对"七个域旗标中只填五个"再做参数化覆盖。建议 Phase 8 前补 `test_format_quality_check_rejects_partial_seven_domain_markers`，把"七域旗标必须齐"作为机器抓手而非依赖人工读29 项。
2. `visual-render-evidence.schema.json` 要求 `screenshot_sha256` 形如 `^[0-9a-f]{64}$`，但未要求每张截图与 `metrics`/`defects` 在同一 `evidence_id`/`run_id` 下落盘。当前负例测试在 `_evidence()` 中固定 SHA_B/SHA_C，未覆盖"screenshot_sha256 与 metrics 取自不同 run"漂移。建议在 `validate_visual_render_evidence` 内强制 `screenshot_sha256 == sha256(screenshot_path 内容)` 的派生绑定或在 schema 加 `screenshot_digest_must_match_artifact_digest`。
3. `visible_text_scan` 依赖工程化/未中文化 token 清单；清单本身的维护未由合同约束，存在"清单漂移"风险。建议在策划书中显式声明 `forbidden_user_visible_tokens`，与运行期扫描清单交叉。
4. 跨格式（pdf/html-ppt/pptx）的 HTML 六类交互触发器不强制，仅 HTML 强制；非 HTML 格式的等价交互占位（如 PDF书签/PPTX 备注/HTML-PPT 键盘）由 `interaction_states.required` 在策划书层把守，但 `validate_visual_render_evidence` 未对非 HTML 格式校验等同的 `interaction_checks` 结构。当前策划书层校验已足够；若想加运行期硬抓，可在非 HTML 分支补 `trigger ∈ {page_load, drill_down, reduced_motion, ...}` 列表。

## 最终裁定

机制补强后能确定性拒绝所列 8 类假通过：只有文件/只有无横向滚动、隐藏字段无入口、标签碰撞、工程化文字、生成者自签、旧摘要背书、七项笼统布尔替代逐域。Codex 已落地 203 项合同/状态图负例与 51 项 Chromium/WebKit 真实回归，覆盖率与合同层守卫、策划书与独立 verdict 三层校验一致闭合。当前冻结 A 报告属机制负例，非本轮正式放行对象；本轮通过对应的是机制合同本身的放行。
