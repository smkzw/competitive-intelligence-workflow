按指定文件做只读复核，并重放上轮关键探针，不以 29 项通过代替判断。代码已看到多处修复；接下来用上轮同一组探针直接打当前入口，确认是否仍能错误纳入或丢掉谱系。# Conference Participant Output: ci_phase6_task61_independent_review - general_grok46 follow-up

## Boundary Check

只读复核指定 10 个文件；用已有 `.venv/bin/python` 重放探针，未改文件、未装依赖、未对外通信。不声称最终产品放行。

## 裁定

**FAIL**

上轮多数入口已关上（ChiCTR 不再接受伪造论文角色；PASI-75 不能凭构念挤进 EASI-75 族；B 早期/OLE/亚组/事后/RWE 在「非关键 II/III」路径可进支持层；周 10 保留窗内差异标签；未知字段 `model_copy` 在权威入口失败关闭；空泛 C 剂量理由不再进核心）。指定测试 29 项通过不能覆盖下面仍可复现的合同漏洞。

## 仍可复现的阻断

### P0 延伸/亚组/事后被错误纳入 B 核心层

- **现象：** `evidence_type` 为 `extension` / `subgroup` / `post_hoc`（以及被标成干预性的 `real_world`）时，只要同时满足目标适应症、II/III 期、有结果、`is_key_or_registration=True`，判定为 **`core`**，而不是支持层。
- **探针：** 上述候选 → `study_role=core`，`matched_rule_ids=('core_b_phase_ii_iii', 'support_b_contextual_evidence')`。核心规则优先级 80，支持规则 60，核心胜出。
- **定位：**
  - `policies/studies/study-role-v1.yaml`：`core_b_phase_ii_iii` 未限制 `evidence_types`（空条件=全部类型）；`support_b_contextual_evidence` 虽列出 `extension, subgroup, post_hoc, real_world`，但优先级更低。
  - `src/ci_workflow/reports/common/study_roles.py`：`StudyRoleRule.matches` 在 `evidence_types` 为空时不过滤；`evaluate_study_role` 按 `(-priority, yaml顺序)` 取胜。
- **后果：** 关键试验的 OLE/亚组/事后分析会与母试验等权进入 B 核心比较。这是错误纳入，不是测试漏标。
- **对照：** 同一证据类型在 `phase_i` 且非关键时 correctly 为 `supporting`。现有测试只覆盖这条安全路径。

### P1 研究角色规则歧义仍可加载

- **现象：** 两条匹配集合重叠、角色不同的规则可以通过 `StudyRolePolicy` 加载；高优先级者改写结果。
- **探针：** 克隆 `core_b_phase_ii_iii` 为 `role=supporting, priority=81` → 加载成功（14 条）；III 期关键试验被判为 `supporting`。
- **定位：** `src/ci_workflow/reports/common/study_roles.py` `StudyRolePolicy._rules_unique` 只拒绝重复 `rule_id` 和（去掉 `rule_id`/`rationale_zh` 后）完全相同的条目，**不拒绝匹配域重叠、角色冲突**。终点/时间窗策略有重叠检查，研究角色没有。
- **后果：** 当前 YAML 已用「核心⊃支持层证据类型」制造 P0；任意后续 YAML 也可把核心改写成支持或相反，审计谱系看起来「命中了两条规则」但胜者只靠优先级。

## 已关闭（本轮探针，不作放行依据）

| 探针 | 当前结果 |
|---|---|
| ChiCTR + 伪造 `publication_role` | `ValueError`：非 NCT 不能从当前记录重算 |
| NCT `model_copy` 改 `role` / `can_replace_primary_report` | 拒绝，须按原文重分类 |
| PASI-75 + `clinical_construct=easi75_response` | `compatible=False`，`未命中终点兼容规则` |
| B 早期有结果 + 具体理由 | `supporting` / `support_b_early_result` |
| 周 10 → 周 12 窗 | `compatible=True`，标签含「第 10 周」「第 12 周附近」 |
| 候选/观察 `model_copy` 未知字段 | 权威入口 `extra_forbidden` |
| C 理由「重要证据」「这是需要关注的重要证据。」 | `excluded`；含「剂量」的具体理由才进 `c_early_decision_domain` |

## Recommended Next Step

在 Task 6.1 合同内修复后再审，不要靠加测试数量过关：

1. `core_b_phase_ii_iii`（及若需对称的 `core_c_phase_ii_iii`）限定 `evidence_types: [standard]`，或让非 `standard` 的支持规则优先级高于核心。
2. 研究角色加载器拒绝「匹配域重叠且角色不同」的规则对。
3. 回归探针必须包含：**III 期 + 关键 + 有结果 + `evidence_type=extension/subgroup/post_hoc` → `supporting`，不得为 `core`。**

Codex 保留最终裁定权。
