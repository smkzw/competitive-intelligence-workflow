# Conference Participant Output: ci_phase6_task61_independent_review - general_pi_antigravity

## Boundary Check

- **工作区与权限合规**：全程仅在当前指定工作区（`.`）运行只读探查与独立推理，未访问或修改生产部署路径，未运行未授权的写入/发布操作。
- **未篡改独立运行报告文件**：未直接向 `runs/conference/ci_phase6_task61_independent_review/general_pi_antigravity.md` 进行文件写入，由 Runner 捕获本独立输出后统一持久化。
- **角色定位与职责边界**：以 `participant 1`（复杂逻辑、证据敏感、高风险矛盾与制品挑战者）身份开展独立审计与逻辑证伪；不替代 Codex 的主会场仲裁、最终临床监管验收与生产签发权。
- **输入基线与上下文载入**：已独立查阅并交叉核对以下基线材料：
  - `context/ci_phase6_task61_independent_review_conference_context.md`
  - `plans/codex_main_venue_ci_phase6_task61_independent_review.md`
  - `.trellis/tasks/08-27-phase-6-task-61-study-role-compatibility/`（`prd.md`、`design.md`、`implement.md`）
  - `runs/execution/ci_phase6_task61_execution/`（`worker_01.md`、`worker_02.md`、`worker_03.md`）
  - 核心源码：`src/ci_workflow/reports/common/study_roles.py`、`src/ci_workflow/reports/b/contracts.py`
  - 版本化策略：`policies/studies/study-role-v1.yaml`、`policies/endpoints/compatibility-v1.yaml`、`policies/timepoints/compatibility-v1.yaml`
  - 自动化测试集：`tests/reports/test_study_role_policy.py`、`tests/reports/b/test_trial_roles.py`、`tests/reports/b/test_endpoint_compatibility.py` 以及全局 896 项单元/合约回归。

---

## Independent Work Product

本审计通过形式化逻辑检查、Pydantic v2 内存对象篡改注入、规则覆盖碰撞探测及边界值测试，对 Task 6.1 交付的“共用研究角色”、“论文角色独立性”与“B 类终点—时间窗兼容合同”完成全流程独立挑战。主要工作产出与核心判定如下：

### 1. 错误纳入与五类默认排除的确定性优先级验证

- **五类机械排除严格生效**：`healthy_volunteer`、`pure_pk_or_be`、`unrelated`（无关适应症）、`observational`、`eap_or_compassionate_use` 均在策略中配置为优先级 10 的 `excluded` 规则；在无高优先级支持理由时，100% 机械判定为 `StudyRole.EXCLUDED`。
- **支持层（Supporting Layer）准入严密性**：
  - 支持层规则 `support_named_problem`（优先级 60）仅在满足全部四重条件时准入：
    1. 显式声明命名问题（`named_issue`）；
    2. 归属封闭问题域（`issue_domain` $\in$ `{safety, regulatory, special_population}`）；
    3. 证据具备不可替代性（`evidence_is_irreplaceable=True`）；
    4. 具体中文理由（`inclusion_rationale_zh`），通过 `_specific_rationale` 正则过滤掉“这项研究很重要”、“具有参考价值”等空泛表述。
  - 当且仅当以上四项全部满足时，原本属于 PK/BE 或观察性的研究方可超越优先级 10 的排除规则进入 `supporting`，且 `matched_rule_ids` 同时保留 `("support_named_problem", "exclude_pure_pk_or_be")` 完整判定链。
- **B 类与 C 类核心层差异化边界**：
  - **B 类核心（Priority 80）**：严格限定目标适应症中已有结果（`has_results=True`）且关键/注册相关（`is_key_or_registration=True`）的 II/III 期干预性试验。一般探索性、未声明关键/注册的早期无对照 II 期研究被严格挡在 B 类核心之外。
  - **C 类设计核心（Priority 80）**：不要求已有结果（容纳进行中关键注册设计），且针对 Phase I/早期试验通过 `c_early_decision_domain` 严格限定六类设计决策域（`dose`, `endpoint`, `adaptive_design`, `population`, `estimand`, `registration_logic`）。
  - **特殊核心（Special Core, Priority 100）**：罕见病、肿瘤或加速开发早期试验必须同时提供具体决策域和不可替代证据方可提升至 `special_core`。

### 2. 论文角色与研究角色物理隔离与防覆盖审查

- **物理模型字段彻底解耦**：`TrialRoleOutput` 分离 `study_role` 与 `publication_role` 两个正交字段，各自维护独立的判定来源（前者来自研究事实+YAML策略，后者来自 PubMed 连接器）。
- **母试验角色免疫性**：通过对比同一母试验绑定 `primary_report` 与 `ad_hoc_analysis` / `review` 的两份 PubMed 记录，母试验的 `study_role`、`matched_rule_ids` 及 `study_role_policy_version` 保持不变，彻底杜绝“论文类型降级导致母试验被移出横向对比”的污染风险。

### 3. 终点与时间窗双键兼容与失败关闭合同审查

- **双键确定性约束**：只有同时命中版本化终点规则与时间窗规则时，才生成 `compatibility_key: (endpoint_rule_id, timepoint_rule_id)` 并标为 `compatible=True`；任一规则不命中即 `compatible=False` 且 `compatibility_key=None`。
- **原始语义绝对保真（Raw Value Preservation）**：
  - 终点观察使用 `_raw_compat_text`，不执行空格压缩或单位擦除，保留原始 `endpoint_id`、`endpoint_definition`、`unit`、`timepoint`、`time_unit` 与 `endpoint_role`。
  - 兼容与不兼容均挂载原始 `observation`，并暴露 `original_endpoint`、`original_definition`、`raw_unit`、`actual_timepoint` 等别名。
- **不兼容原因中文差异标签审计**：
  - 当出现方向不一致、单位不可直接换算、分析形式不兼容、时间点超出范围、时间单位未知时，确定性生成包含具体中文描述的 `difference_labels_zh`（例如 `("方向不兼容", "单位不可直接换算", "分析形式不兼容")`），禁止空标签或静默丢弃。
- **YAML 规则重叠与歧义静态阻断**：
  - `EndpointCompatibilityPolicy` 在加载时通过多项式组合遍历校验：同构念/同终点且方向相同、单位重叠、分析形式重叠的规则直接抛出 `EndpointCompatibilityError("终点兼容规则存在重叠歧义")` 拒绝加载。
  - `TimepointCompatibilityPolicy` 在加载时校验：同单位闭区间 $[min_1, max_1]$ 与 $[min_2, max_2]$ 若存在交集（$\max(min_1, min_2) \le \min(max_1, max_2)$）立即抛出异常拒绝加载，保证时间窗互斥无歧义。

---

## Evidence And Assumptions

### 1. 关键测试与行为验证证据

- **自动化测试套件**：
  - `pytest tests/reports/test_study_role_policy.py tests/reports/b/test_trial_roles.py tests/reports/b/test_endpoint_compatibility.py`：**19/19 passed**。
  - 核心回归集 `pytest tests/reports/ tests/unit/ tests/contract/ tests/integration/reports/`：**896/896 passed**（耗时 17.01s）。
- **静态类型与代码质量**：
  - `mypy --strict src/ci_workflow/reports/common/study_roles.py src/ci_workflow/reports/b/contracts.py`：**Success: no issues found in 2 source files**。
  - `ruff check`：全部检查通过。

### 2. 探针实验与边界证伪证据

通过受控 Python 执行环境注入多种攻击向量与异常场景，记录到以下确定性事实：

| 实验编号 | 攻击/边界场景 | 输入特征 | 观察到的系统行为 | 判定结论 |
| :--- | :--- | :--- | :--- | :--- |
| **EXP-01** | 手工注入字典伪造角色 | `{"study_id": "...", "study_role": "excluded"}` | `StudyCandidate.model_validate` 触发 `extra_forbidden` 校验异常 | **通过（字典入口失败关闭）** |
| **EXP-02** | 伪造篡改 NCT 论文分类 | `publication.model_copy(update={"role": "review"})` | `_validated_publication` 重新执行 PubMed 分类比对，抛出 `ValueError("论文角色必须由当前论文记录和目标试验重新分类")` | **通过（NCT 重新计算防篡改）** |
| **EXP-03** | 空泛纳入理由拦截 | `inclusion_rationale_zh="这项研究很重要。"` | `_specific_rationale` 返回 `False`，拒绝准入核心/支持层，判定为 `EXCLUDED` | **通过（文本空泛过滤有效）** |
| **EXP-04** | 构念明确但终点名未列入 | `endpoint_id="custom_x", clinical_construct="easi75_response"` | 成功命中 `endpoint-easi75-response-v1`，生成有效兼容键 | **通过（构念兼容扩展性）** |
| **EXP-05** | 构念冲突拦截 | `endpoint_id="easi75", clinical_construct="nasal_polyp_score"` | 构念过滤后候选项为空，返回 `compatible=False`，标签 `("临床构念不兼容",)` | **通过（显式构念冲突失败关闭）** |
| **EXP-06** | 复合维度不兼容 | 终点方向相反 + 单位为分数 + 分析形式为绝对值 | 正确识别 3 个维度的不兼容，标签返回 `("方向不兼容", "单位不可直接换算", "分析形式不兼容")` | **通过（多原因全量保留）** |
| **EXP-07** | 单位无换算跨度拦截 | `timepoint=84, time_unit="day"` 匹配周规则 | 仅在 `TimeUnit.DAY` 规则集合中查找，返回 `("时间点超出兼容范围",)`，未发生模糊换算（84/7=12周） | **通过（初版无隐式单位换算）** |
| **EXP-08** | Pydantic v2 `model_copy` 注入未声明属性 | `c.model_copy(update={"study_role": "core"})` | `candidate.model_dump()` 默认仅导出 `model_fields`，篡改字段被忽略，输出仍基于规则重新判定 | **逻辑安全但存在静默吞没（见风险 1）** |
| **EXP-09** | 非 NCT 试验标识符论文注入 | `study_id="CTR20220001"` 传入伪造 `ClassifiedPublication` | 因 `_NCT_ID.fullmatch` 为 `None`，跳过 `classify_pubmed_records` 校验 | **存在边界漏洞（见风险 2）** |

---

## Risks, Gaps, And Verification Needs

### 高风险缺陷与架构漏洞识别

#### 1. 【高风险/实现陷阱】Pydantic v2 `model_copy(update=...)` 额外字段被 `model_dump()` 静默丢弃而非失败关闭
- **事实依据**：
  在 `study_roles.py` 的 `_validated_candidate` 与 `contracts.py` 的 `_validated_observation` 中：
  ```python
  raw = (
      candidate.model_dump(mode="python", warnings=False)
      if isinstance(candidate, StudyCandidate)
      else dict(candidate)
  )
  return StudyCandidate.model_validate(raw)
  ```
  Pydantic v2 中，`model_copy(update={...})` 会将任意键值直接写入实例的 `__dict__`（绕过 `extra="forbid"`）。当随后调用 `candidate.model_dump()` 时，Pydantic 默认只迭代 `model_fields`，导致注入的未知字段或伪造字段在导出为 dict 时被**静默剔除**，紧接着的 `model_validate(raw)` 看到的是干净字典从而成功通过。
- **潜在危害**：
  虽然 `evaluate_study_role` 与 `match_endpoint_compatibility` 最终是根据合法字段和策略文件重新计算输出，使得被注入的 `tampered.__dict__["study_role"]` 无法直接篡改结果；但是当调用方传递携带非法/拼写错误字段的 `BaseModel` 对象时，系统失去了“立即抛出 `ValidationError` 失败关闭”的契约防御能力。
- **整改建议**：
  在重新校验入口，改用 `dict(candidate.__dict__)` 或显式检查 `set(candidate.__dict__.keys()) <= set(Model.model_fields.keys())`，使内存对象篡改与 raw dict 具有相同的失败关闭行为：
  ```python
  raw = dict(candidate.__dict__) if isinstance(candidate, BaseModel) else dict(candidate)
  return StudyCandidate.model_validate(raw)
  ```

#### 2. 【中高风险/边界漏洞】非 NCT 试验标识符（如中国 CTR 登记号）论文重新分类校验被绕过
- **事实依据**：
  在 `reports/b/contracts.py` 的 `_validated_publication` 中：
  ```python
  normalized_study_id = study_id.strip().upper()
  if _NCT_ID.fullmatch(normalized_study_id):
      expected = classify_pubmed_records(
          (validated.record,), target_nct_ids=(normalized_study_id,)
      )[0]
      if (
          validated.role != expected.role
          or validated.matched_nct_ids != expected.matched_nct_ids
          or validated.classification_signals != expected.classification_signals
          or validated.rationale_zh != expected.rationale_zh
      ):
          raise ValueError("论文角色必须由当前论文记录和目标试验重新分类")
  ```
- **潜在危害**：
  该防篡改检查通过正则表达式 `_NCT_ID = re.compile(r"NCT[0-9]{8}", re.IGNORECASE)` 进行了门禁过滤。如果未来 B/C 报告引入中国临床试验登记号（如 `CTR20220001`）或内部项目编号，`_NCT_ID.fullmatch` 将返回 `None`，导致系统跳过 `classify_pubmed_records` 的权威重新计算，直接信任传入的 `ClassifiedPublication` 数据。
- **整改建议**：
  明确定义非 NCT 标识符的跨源校验合同：若 PubMed 连接器暂不支持非 NCT 的文本识别，则对于非 NCT 试验绑定的论文，强制回退至 `publication_role="unclassified"` 并记录审计警告，或扩展 `classify_pubmed_records` 支持 CTR 正则。

#### 3. 【中风险/策略表达力】时间窗互斥约束禁止了“不同精度重叠窗”的共存
- **事实依据**：
  `TimepointCompatibilityPolicy` 中的 `_time_rules_are_unique` 强制任意两条同单位规则的闭区间不得有任何重叠（$\max(min_1, min_2) \le \min(max_1, max_2)$ 即报错）。
- **影响评估**：
  这一约束有效杜绝了歧义，但在临床实际中，若存在“第 12 周主要分析窗 $[10, 14]$ 周”与“第 12 周严格分析窗 $[11.5, 12.5]$ 周”等多精度场景时，系统将直接拒绝加载策略。当前 Task 6.1 阶段这一严格设计保证了失败关闭，但在后续 Phase 6 扩展时，如需支持层次化时间窗，需引入优先级或构念绑定时间窗。

---

## Recommended Next Step

1. **主会场决议与代码微调授权（Bounded Question for Codex）**：
   - **问题 1**：对于 `_validated_candidate` 和 `_validated_observation` 中 Pydantic v2 `model_copy` 注入字段被 `model_dump()` 静默丢弃的现象，Codex 是否授权在终验前补充 `dict(candidate.__dict__)` 显式失败关闭检查？
   - **问题 2**：针对非 NCT 试验标识符（如 `CTR...`），当前版本是否统一约定暂只支持 `NCT` 跨源核验，非 NCT 一律判定为 `unclassified` 并在文档中明确？
2. **测试与回归归档**：
   - 确认 Task 6.1 的 3 份目标测试、策略 YAML 与共用合同均已通过严格类型与逻辑验证；
   - 由 Codex 在主会场统一整合 `verdict.md`，执行 `git diff --check` 与提交：`feat: define auditable study roles and report B endpoint compatibility`；
3. **Phase 6 后续任务衔接**：
   - 进入 Task 6.2（B 类报告分析与横向对比流水线构建），将本合同正式接入数据流，确保数据输入端严格消费 `StudyCandidate` 与 `EndpointObservation`。
