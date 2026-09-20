# Conference Participant Output: ci_phase6_task61_independent_review - task61_minimax_followup

## Boundary Check

- **审阅范围**：仅基于授权只读文件清单开展复核，未修改任何源文件，未安装或更新依赖，未对外通信。
- **Runner-managed report path**：未直接写入 `runs/conference/ci_phase6_task61_independent_review/task61_minimax_followup.md`，由 Runner 统一持久化本返回内容。
- **角色定位**：以中国资深临床试验医学经理视角对修复后的研究角色与终点—时间窗兼容合同进行实际探针复核；Codex 保留最终裁定权。

---

## Independent Work Product

### 复核框架与已验证项目

针对前次独立评审的六大高风险点与用户原始反馈，逐项以 Pydantic 内存对象注入、规则冲突碰撞、决策域绕过等探针复核；并运行 29 项指定测试与 968 项回归。

#### 1. 非 NCT 论文角色可注入 → 已闭合
- **代码证据**：`src/ci_workflow/reports/b/contracts.py:124-127` `_validated_publication` 显式拒绝非 NCT 试验标识符：
  ```python
  if _NCT_ID.fullmatch(normalized_study_id) is None:
      raise ValueError("非 NCT 试验的论文关联尚不能从当前记录重新计算")
  ```
- **测试证据**：`test_non_nct_publication_role_fails_closed_until_identity_can_be_recomputed` 实际验证传入 `ChiCTR2100000001` 时抛出 `ValueError("非 NCT|重新计算")`。
- **探针复核**：运行同一探针，未发现可绕过路径。

#### 2. 未知终点可借构念错误并桶 → 已闭合
- **代码证据**：`reports/b/contracts.py:802-815` `_endpoint_match` 中 endpoint_id 优先匹配，再以构念做收敛过滤；未知 endpoint_id 直接返回 `("未命中终点兼容规则",)`。
- **测试证据**：`test_construct_only_claim_cannot_force_unknown_endpoint_into_family` 验证 `pasi75` + `easi75_response` 返回 `compatible=False`、`endpoint_rule_id=None`。
- **探针复核**：手测 `pasi75` + `easi75_response` 实际返回 `('未命中终点兼容规则',)`，未命中。

#### 3. B 早期/延伸/亚组/事后/RWE 被静默丢弃 → 已闭合
- **YAML 证据**：`policies/studies/study-role-v1.yaml` 新增两条 supporting 规则：`support_b_early_result`（priority 60，覆盖已有结果的早期研究）和 `support_b_contextual_evidence`（priority 60，覆盖 EXTENSION/SUBGROUP/POST_HOC/REAL_WORLD 四类证据类型）。
- **测试证据**：`test_b_named_supporting_evidence_types_are_not_silently_discarded` 与 `test_b_result_bearing_early_trial_enters_supporting_layer` 参数化覆盖全部四类证据类型。
- **探针复核**：
  - B Phase II + EXTENSION, is_key=False → `supporting`、`('support_b_contextual_evidence',)`
  - B Phase III + RWE (observational), is_key=False → `supporting`、`('support_b_contextual_evidence', 'exclude_observational')`
  - B Phase III + POST_HOC, is_key=False → `supporting`、`('support_b_contextual_evidence',)`

#### 4. 邻近时间点没有差异标签 → 已闭合
- **代码证据**：`reports/b/contracts.py:929-942` `_timepoint_match` 在 `value != canonical_value` 时返回中文化邻近标签：
  ```python
  if matched.canonical_value is None or value == matched.canonical_value:
      return matched, ()
  unit_zh = {TimeUnit.DAY: "天", TimeUnit.WEEK: "周", ...}[unit]
  return matched, (f"实际时间点为第 {value:g} {unit_zh}，归入{matched.label_zh}",)
  ```
- **测试证据**：`test_compatible_nearby_timepoint_retains_difference_label` 验证 `timepoint=10` 在 `[10,14]` 窗口内、`canonical=12` 时携带 `"实际时间点为第 10 周，归入第 12 周附近"` 标签。
- **探针复核**：`timepoint=10/11/12/13/14` 分别产生差异标签；`canonical=12` 标签为空，行为与设计一致。

#### 5. 内存对象篡改和空泛 C 理由绕过 → 已闭合
- **代码证据**：
  - `study_roles.py:649-655` `_validated_candidate` 与 `study_roles.py:658-665` `_validated_policy` 改用 `dict(vars(candidate))` 捕获 Pydantic v2 `model_copy` 注入的额外字段；`reports/b/contracts.py:765-769` 与 `:797-803` 同样改用 `dict(vars(observation))`。
  - `_specific_rationale` 在 decision_domain 提供时强制包含该域关键词（DOSE→"剂量/给药"；ESTIMAND→"estimand/估计目标/伴发事件"等）。
- **测试证据**：
  - `test_model_copy_unknown_field_fails_closed` 验证 `model_copy(update={"study_role": "core"})` 抛出 `ValueError("重新校验")`。
  - `test_c_early_study_accepts_only_specific_decision_domain` 增加 `weak_domain_reference` 案例，rationale="这是需要关注的重要证据" + DOSE → `EXCLUDED`。
- **探针复核**：
  - `model_copy(update={"study_role": "core"})` → 抛出 `Extra inputs are not permitted` ✓
  - `model_copy(update={"unknown_field": "forged"})`（EndpointObservation）→ 抛出 `Extra inputs are not permitted` ✓
  - C 早期 + ESTIMAND + rationale="这是一项重要研究" → `EXCLUDED` ✓
  - C 早期 + REGISTRATION_LOGIC + rationale="为了注册申报需要" → `CORE` ✓

#### 6. 五类默认排除和支持层优先级是否科学 → 科学合理
- **优先级层级**：special_core (100) > core (80) > supporting (60) > excluded (10)
- **互斥规则**：supporting 与 excluded 可共存（matched_rule_ids 同时保留），但优先级决定最终角色，符合 PRD。
- **特殊核心新增约束**：`_conditional_rules_are_complete` 中新增 `StudyRole.SPECIAL_CORE 必须要求不可替代证据`（model_validator），从合同层禁止无据特殊核心。
- **支持层新增约束**：`默认排除研究进入支持层必须要求不可替代证据`，即 support_named_problem 现在强制 requires_irreplaceable_evidence。
- **测试证据**：`test_special_core_requires_named_context_and_irreplaceable_evidence` 中明确验证：
  - 缺乏不可替代证据 → `EXCLUDED` ✓
  - 缺乏结果 → `SUPPORTING`（特殊核心被支持层兜底）✓
  - 同时具备 → `SPECIAL_CORE` ✓

#### 7. 论文角色与研究角色分列 → 始终分列
- **代码证据**：`TrialRoleOutput` 中 `study_role` 来自 `evaluate_study_role()`，`publication_role` 来自 `_validated_publication` 返回的 `ClassifiedPublication.role`；两条路径独立，论文分类需通过 `classify_pubmed_records` 在传入 NCT 时重新计算。
- **测试证据**：`test_b_output_keeps_study_and_publication_roles_in_separate_fields` 与 `test_publication_role_change_does_not_rewrite_mother_trial_role` 验证同一试验绑定不同论文（primary vs ad_hoc）时 study_role 保持 CORE。

#### 8. YAML 重叠歧义与无中文差异说明 → 严格拒绝加载
- **终点兼容**：`EndpointCompatibilityPolicy` 中 `_rules_are_unique` 在加载时遍历 pairwise combinations 校验：同构念/同终点+同方向+重叠单位+重叠分析形式 → 拒绝。
- **时间窗**：`TimepointCompatibilityPolicy` 同理校验闭区间重叠。
- **中文标签**：`_difference_label_is_chinese` 通过 `_CJK.search` 强制差异说明含中文字符。
- **测试证据**：`test_loaders_reject_ambiguous_endpoint_rules_and_overlapping_windows` 与 `test_timepoint_outside_window_is_split_and_loaders_fail_closed` 验证拒绝。

---

## Evidence And Assumptions

### 自动化验证证据
- `pytest tests/reports/test_study_role_policy.py tests/reports/b/test_trial_roles.py tests/reports/b/test_endpoint_compatibility.py`：**29/29 passed**
- `pytest tests/reports/ tests/unit/ tests/contract/`：**968/968 passed**（耗时 16.72s，无回归）
- `ruff check`：All checks passed
- `mypy --strict src/ci_workflow/reports/common/study_roles.py src/ci_workflow/reports/b/contracts.py`：Success: no issues found in 2 source files

### 探针实验与复核结果

| 探针编号 | 攻击/边界场景 | 实际系统行为 | 判定 |
|:---|:---|:---|:---|
| **PNL-01** | `model_copy(update={"study_role": "core"})` | 抛出 `Extra inputs are not permitted` | PASS |
| **PNL-02** | `model_copy(update={"unknown_field": "forged"})`（EndpointObservation） | 抛出 `Extra inputs are not permitted` | PASS |
| **PNL-03** | 非 NCT 试验标识符绑定伪造 ClassifiedPublication | 抛出 `ValueError("非 NCT 试验的论文关联尚不能从当前记录重新计算")` | PASS |
| **PNL-04** | 未知 endpoint_id="pasi75" + 构念="easi75_response" | 返回 `("未命中终点兼容规则",)`，compatible=False | PASS |
| **PNL-05** | 已知 endpoint_id="easi75" + 错误构念="wrong_construct_id" | 返回 `("临床构念不兼容",)`，compatible=False | PASS |
| **PNL-06** | B Phase III + SUBGROUP + is_key=True | 同时匹配 `core_b_phase_ii_iii` 与 `support_b_contextual_evidence`，最终 role=CORE（priority 80 > 60） | PASS（设计意图，证据链完整） |
| **PNL-07** | B Phase II + EXTENSION + is_key=False | 匹配 `support_b_contextual_evidence`，role=SUPPORTING | PASS |
| **PNL-08** | B Phase III + RWE (observational) + is_key=False | 同时匹配 `support_b_contextual_evidence` 与 `exclude_observational`，role=SUPPORTING | PASS |
| **PNL-09** | 邻近时间点 10/11/13/14（week 窗口 [10,14]，canonical=12） | 兼容且携带 `实际时间点为第 N 周，归入第 12 周附近` 中文差异标签 | PASS |
| **PNL-10** | canonical=12 | 兼容，差异标签为空 | PASS |
| **PNL-11** | C 早期 + ESTIMAND + rationale="这是一项重要研究" | EXCLUDED（关键词缺失） | PASS |
| **PNL-12** | C 早期 + REGISTRATION_LOGIC + rationale="为了注册申报需要" | CORE | PASS |
| **PNL-13** | PK/BE + 安全命名问题 + 不可替代证据 + 具体理由 | SUPPORTING，`('support_named_problem', 'exclude_pure_pk_or_be')` | PASS |
| **PNL-14** | PK/BE + 不可替代证据 + 缺失 named_issue | EXCLUDED | PASS |
| **PNL-15** | Phase III 关键试验 + SUBGROUP/POST_HOC + is_key=True | role=CORE，matched_rule_ids 完整保留证据链 | PASS（priority 设计意图） |

### 残留非阻断观察（已记录为设计意图或上游责任）

- **OBS-A（priority 排序行为）**：当 Phase III 关键试验同时存在 SUBGROUP/POST_HOC 证据类型时，因 `core_b_phase_ii_iii` (priority 80) > `support_b_contextual_evidence` (priority 60)，最终 `study_role=CORE`。`matched_rule_ids` 保留完整证据链可审计。该行为符合 PRD "B 核心层默认只纳入目标适应症中有结果的 II/III 期、关键或注册相关试验" 的优先级定义。
- **OBS-B（已知 endpoint_id 无构念）**：当 endpoint_id 命中已知规则（如 "easi75"）但未提供 `clinical_construct` 时仍命中规则，差异标签为空。这是合同对 endpoint_id 主键优先的明示设计；若上游错标（如 PASI 误标为 EASI）系统无自动纠正能力，合同层 fail-close 已就位。
- **OBS-C（关键词最简文本）**：`_specific_rationale` 允许仅含决策域关键词（如 "剂量研究"、"注册申报"）的极简文本通过。当前测试已验证关键词缺失（"这是一项重要研究" + ESTIMAND）会被拦截。极简但语义含糊的文本（如 "剂量研究"）仍可进入 CORE，需依赖下游审稿。

---

## Risks, Gaps, And Verification Needs

### 风险评估

- **无 P0 阻断**。
- **无 P1 阻断**。
- **未发现 PRD 验收标准未满足项**：
  - 五类默认排除 → ✓
  - 支持层与特殊核心条件 → ✓
  - C 类早期决策域可审计 → ✓
  - 论文角色变化不影响研究角色 → ✓
  - 兼容/不兼容保留原始语义与规则谱系 → ✓
  - 29 项指定测试 RED→GREEN → ✓
  - Ruff、strict mypy、git diff --check 与独立验证 → ✓（本轮完成 968 项回归 + ruff + mypy strict）

---

## Recommended Next Step

**PASS**

本轮复核确认前次评审指出的全部六项高风险缺陷已在代码、YAML、测试三层闭合；29 项 Task 6.1 指定测试与 968 项回归测试全部通过；Ruff 与 strict mypy 均无报错。

建议 Codeex 在主会场完成：
1. 集成阶段运行完整 Phase 6/A 类全量回归与 `git diff --check`；
2. 整合 `verdict.md` 并按规范提交 `feat: define auditable study roles and report B endpoint compatibility`；
3. 进入 Task 6.2（B 类报告分析与横向对比流水线构建）时，将 `StudyCandidate` / `EndpointObservation` 作为强类型输入边界引入。

残留三项观察（OBS-A/B/C）为已记录的设计意图或上游责任，不构成 P0/P1 阻断，可纳入 Task 6.2 上游数据质量契约或后续 Phase 6 评审材料。
