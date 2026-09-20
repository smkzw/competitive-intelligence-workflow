# Conference Participant Output: ci_phase6_task61_independent_review - task61_minimax_followup_round2

## Boundary Check

- **审阅范围**：仅基于授权只读文件清单 `src/ci_workflow/reports/common/study_roles.py`、`policies/studies/study-role-v1.yaml`、`tests/reports/test_study_role_policy.py` 开展复核。
- **未修改任何源文件、未安装依赖、未对外通信**。
- **Runner-managed report path**：未直接写入 `runs/conference/ci_phase6_task61_independent_review/task61_minimax_followup_round2.md`，由 Runner 统一持久化本返回内容。

---

## Independent Work Product

### 探针复核（生产 v1 策略实际重放）

按 Codex 修复后的策略 `policies/studies/study-role-v1.yaml`，重新执行上一轮评审关注的关键 III 期证据类型探针与冲突规则探针。

#### 关键 III 期 + 四类证据类型（必须为 SUPPORTING）

| 探针 | evidence_type | has_results | is_key_or_registration | 期望 study_role | 实际 study_role | matched_rule_ids | 判定 |
|:---|:---|:---:|:---:|:---|:---|:---|:---:|
| **PNL-III-01** | EXTENSION（interventional） | True | True | SUPPORTING | `supporting` | `('support_b_contextual_evidence',)` | **PASS** |
| **PNL-III-02** | SUBGROUP（interventional） | True | True | SUPPORTING | `supporting` | `('support_b_contextual_evidence',)` | **PASS** |
| **PNL-III-03** | POST_HOC（interventional） | True | True | SUPPORTING | `supporting` | `('support_b_contextual_evidence',)` | **PASS** |
| **PNL-III-04** | REAL_WORLD（observational） | True | True | SUPPORTING | `supporting` | `('support_b_contextual_evidence', 'exclude_observational')` | **PASS** |
| **PNL-III-05** | STANDARD（母试验自身） | True | True | CORE | `core` | `('core_b_phase_ii_iii',)` | **PASS**（母试验自身仍为核心） |

判定依据：
- YAML 第 18 行 `core_b_phase_ii_iii` 显式限定 `evidence_types: [standard]`，匹配时只命中 evidence_type=standard 的候选。
- YAML 第 56 行 `support_b_contextual_evidence` 限定 `evidence_types: [extension, subgroup, post_hoc, real_world]`，PNL-III-01~04 全部命中该规则，study_role=supporting。
- 母试验（evidence_type=standard）不命中 contextual_evidence 规则，仅命中 core_b_phase_ii_iii，最终 role=core，符合 Codex 裁定："母试验可为核心，但延伸、亚组、事后和真实世界结果本身只能进入支持层"。

#### 冲突规则探针

| 探针 | 场景 | 期望 | 实际 | 判定 |
|:---|:---|:---|:---|:---:|
| **PNL-CONFLICT-01** | 复制 `core_b_phase_ii_iii` 适用条件 + `role=supporting` + 不同 priority | 拒绝加载 | `StudyRolePolicyError: 研究角色规则适用条件相同但角色冲突` | **PASS** |
| **PNL-CONFLICT-02** | 复制 `core_b_phase_ii_iii` 完全相同（仅 rule_id 与 rationale_zh 不同） | 拒绝加载 | `StudyRolePolicyError: 研究角色规则条目不得重复` | **PASS** |

判定依据：
- `StudyRolePolicy._rules_unique` 的 eligibility_signature 路径（`study_roles.py:583-606`）：对 `role/priority/requires_*` 等排除字段之外的所有适用条件生成签名，若同一签名映射到不同 role 则拒绝加载（"适用条件相同但角色冲突"）。
- 同时保留了原有"规则条目不得重复"路径（body 签名），覆盖完全重复规则。

#### 额外探针：母试验特殊核心路径

| 探针 | 场景 | 期望 | 实际 | 判定 |
|:---|:---|:---|:---|:---:|
| **PNL-SP-01** | B Phase I 罕见病 + 命名问题 + 不可替代 + 决策域 + 具体理由 + standard | SPECIAL_CORE | `special_core` / `('special_core_early',)` | **PASS** |
| **PNL-SP-02** | C Phase I 罕见病 + 同上 | SPECIAL_CORE | `special_core` / `('special_core_early_c',)` | **PASS** |
| **PNL-SP-03** | C Phase I 普通病 + 决策域 + 具体理由 + standard | CORE | `core` / `('c_early_decision_domain',)` | **PASS** |
| **PNL-SP-04** | C Phase I + 决策域 + 空泛理由 "这项研究很重要" | EXCLUDED | `excluded` / `()` | **PASS** |
| **PNL-SP-05** | C Phase I + 决策域 + 弱关键词 "这是需要关注的重要证据" | EXCLUDED | `excluded` / `()` | **PASS** |

### 自动化验证

- `pytest tests/reports/test_study_role_policy.py`：**21/21 passed**（含 `test_key_phase_iii_contextual_evidence_stays_supporting` 参数化 4 类证据类型，`test_study_policy_rejects_same_eligibility_with_conflicting_roles`）
- `pytest tests/reports/ tests/unit/ tests/contract/`：**973/973 passed**（耗时 17.98s，无回归）
- `ruff check src/ci_workflow/reports/common/study_roles.py tests/reports/test_study_role_policy.py`：All checks passed
- `mypy --strict src/ci_workflow/reports/common/study_roles.py`：Success: no issues found in 1 source file

### 残留设计意图（非阻断）

- **OBS-D（eligibility signature 排除字段）**：当前 `eligibility_signature` 排除 `role/priority/requires_*` 字段，因此"同适用条件 + 同 role + 高 priority"的两条规则可共存（不被规则冲突检测器拦截）。生产 v1 YAML 中所有核心/特殊核心规则均已显式限定 `evidence_types: [standard]`，从策略内容层面消除了此绕过路径；如未来引入新规则需遵守相同约束。
- **OBS-E（rule.matching 的 evidence_types 默认空）**：当某条规则未声明 `evidence_types` 时，`matches()` 中 `if self.evidence_types and candidate.evidence_type not in self.evidence_types: return False` 会让空集合视为"通配"。当前所有适用规则（`support_b_contextual_evidence`、`exclude_*`）均已显式声明 `evidence_types` 或与 evidence_type 无关（如 design_category 排除路径），生产策略无绕过风险。

---

## Evidence And Assumptions

- **代码层证据**：
  - `src/ci_workflow/reports/common/study_roles.py:404-407`：`StudyRoleRule.evidence_types` 字段及唯一性校验已就位。
  - `src/ci_workflow/reports/common/study_roles.py:545-547`：`matches()` 中 `if self.evidence_types and candidate.evidence_type not in self.evidence_types: return False`。
  - `src/ci_workflow/reports/common/study_roles.py:583-606`：`StudyRolePolicy._rules_unique` 中 eligibility_signature 路径检测同适用条件但不同角色的冲突。
- **策略层证据**：`policies/studies/study-role-v1.yaml` 中所有 B/C 核心与特殊核心规则均显式 `evidence_types: [standard]`；`support_b_contextual_evidence` 显式列出 `[extension, subgroup, post_hoc, real_world]`。
- **测试层证据**：
  - `test_key_phase_iii_contextual_evidence_stays_supporting` 参数化四类证据类型，断言 `study_role is SUPPORTING` 且 `core_b_phase_ii_iii not in matched_rule_ids`。
  - `test_study_policy_rejects_same_eligibility_with_conflicting_roles` 构造 `core_b_phase_ii_iii` 适用条件 + `role=supporting` 的副本，断言抛出 `ValueError("角色冲突")`。
  - `test_study_policy_rejects_semantically_duplicated_role_rules` 断言完全重复规则抛出 `ValueError("重复|歧义")`。

---

## Risks, Gaps, And Verification Needs

- **无 P0 阻断**。
- **无 P1 阻断**。
- PRD 第 14 行 "事后分析、综述、支持论文或主要报告的论文角色变化不得改写母试验角色" 与第 11 行 "支持层必须指向一个已命名的安全性、监管或特殊人群问题" 在当前实现下完全成立：
  - 论文角色变化通过 `TrialRoleOutput` 独立字段（`study_role` 与 `publication_role` 分列）保证不覆盖母试验；
  - 支持层规则 `support_named_problem` 强制要求 `named_issue` + `issue_domain ∈ {safety, regulatory, special_population}` + `evidence_is_irreplaceable=True` + 具体中文理由。

---

## Recommended Next Step

**PASS**

本轮复核确认 Codex 修复后的策略与代码在生产 v1 YAML 上完全满足裁定要求：
1. 关键 III 期的 extension/subgroup/post_hoc/real_world 四类证据全部为 SUPPORTING，且 `core_b_phase_ii_iii` 不在 `matched_rule_ids` 中；
2. 母试验自身（evidence_type=standard）仍为 CORE；
3. 同适用条件但不同角色的规则在加载时被拒绝；
4. 21 项 Task 6.1 研究角色测试 + 973 项回归测试全部通过，ruff 与 strict mypy 零报错。

Codex 可在主会场整合 Phase 6 验收材料并按规范提交 `feat: define auditable study roles and report B endpoint compatibility`；进入 Task 6.2 时只需保持 `StudyCandidate.evidence_type` 的来源契约（结构化输入），不得绕过 `StudyRolePolicy` 显式重新计算。
