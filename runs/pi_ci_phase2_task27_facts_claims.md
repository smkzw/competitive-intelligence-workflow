全部对抗探针执行完毕，机械检查与攻击面证据齐备。以下是验收报告。

---

# Task 2.7 独立验收

## 结论

**PASS（建议接受）**。P0=0，P1=0，P2=6。

六项机械检查全部真实通过，且与构建者 green 记录逐项一致（4/4 组合、182/182 全库、Ruff、mypy --strict、PACKAGE_OK、diff 干净）。对抗检查中所有会造成原文错配、冲突丢失、计算声明错值或综合判断冒充直接事实的路径均被拦截；发现的 6 项缺陷全部为 P2 边缘漂移，不阻断本任务 ER01–ER04 合同验收，建议下一阶段修复。事实/声明结构合同与后续真实临床来源抽取、GateSpec、报告层严格区分，未越界验收。

## 运行与读取证据

逐行读取的合同/实现文件（20 项）：`context/ci_phase2_task27_facts_claims_context.md`、设计 v1.2（§8.1–8.7 科学真源合同、§19 测试责任）、ADR 0010、`prd/design/implement.md`、`domain/{evidence,facts,claims,enums,ids}.py`（全文 raw）、`capabilities/{extraction_normalization,resolution}.py`（全文 raw）、`schemas/{fact,claim}.schema.json`、`package-manifest.json`、两个集成测试（全文 raw）、`docs/acceptance/runs/task-2.7/{red,green}.txt`。

真实运行结果（2026-08-12，工作树当前状态）：

| 命令 | 结果 |
|---|---|
| `uv run pytest tests/integration/test_source_to_claim_chain.py tests/integration/test_conflicts_preserved.py -q` | **4 passed in 0.07s** |
| `uv run pytest -q` | **182 passed in 5.55s** |
| `uv run ruff check src tests` | **All checks passed!** |
| `uv run mypy --strict src` | **Success: no issues found in 44 source files** |
| `uv run ci-workflow package verify --root .` | **PACKAGE_OK version=0.1.0a0 stage=phase-0-task-0.4** |
| `git diff --check` 与 `git status --short` | diff 无输出（干净）；status 与会话快照一致（M package-manifest.json + 14 个 untracked 新文件） |

green.txt 声称的 4/182/全部通过/PACKAGE_OK 全部复现；red.txt 的 ER01–ER04 预期 RED 与"缺模块/缺类型"语义一致。另执行 9 项对抗探针（运行验证，非仅读码）。

## 事实入口与版本攻击

**攻击已拦截：**
- **来源版本与重开原文核验**：`verify_reopened_fragment` 强制 `source_version_id` 与片段绑定一致；`VerifiedEvidenceFragment` 校验片段摘要（`sha256(original_text)` == `content_sha256`）且重开原文与片段原文逐字相等；`AtomicFactExtractionInput._raw_value_is_the_reopened_fragment` 强制事实 `raw_value` 等于精确重开的最小片段。原文错配路径被双重相等约束封死。
- **字段全集**：`AtomicFactVersion` 32 字段覆盖 §8.3 要求的主体、字段、原始表达、规范化值、单位、上下文、组别/队列、人群、时间点或时间窗（探针确认两者皆空被 Pydantic 拒绝）、分子/分母（分母 >0、分子 ≤分母）、来源片段、抽取方法、规范化方法、质量状态、披露成熟度、创建版本、有效/发布日期。
- **次日重跑身份稳定**：`extract_atomic_fact` 的版本负载排除 `created_at`，测试断言同内容次日 `fact_version_id` 相等，实测通过。
- **状态语义分层**：`RouteAttemptResult`/`RouteCompletion`/`FactDisclosureState` 为独立枚举，路由失败无法写入事实披露状态；`REPORTED_ZERO` 必须有零值原文证据（正则匹配）且分子必为 0（探针：分子 5 被拒）、规范值必为 0；`NOT_APPLICABLE` 必须链接适用性谓词；`UNRESOLVED_DUE_TO_ROUTE` 必须链接路由回执。

## 规范化与冲突攻击

**攻击已拦截：**
- 规范化生成新版本（`supersedes_fact_version_id` 链式），`raw_value` 保留，记录 `rule_id/rule_version/method_zh/reverse_expression`；`AtomicFactVersion` 校验规范化记录与事实的 `normalized_value/normalized_unit/raw_value` 三方一致；`reverse_normalized_fact` 可逆（测试断言返回原始 "-2.10"）；规则版本升级（1.0→1.1）产生新版本且不覆盖前版。
- 重复规范化幂等：同一规则作用于同一原始事实时版本标识稳定（测试断言 + 探针复现一致）。
- 冲突非先到先得：`build_fact_conflict_set` 要求 ≥2 个不同观察值、同字段同比较范围（实体/字段/上下文/组别/人群/时间/单位）、成员排序按版本 ID 确定性排序，`resolution_state` 恒为 `"open"` 且不预选事实、不填裁决；测试证明输入顺序无关、冲突集 ID 稳定、两个来源事实均保留 ACCEPTED 且不被取代。

## 声明链与 schema 攻击

**攻击已拦截：**
- 声明只链接已接受事实：`create_*_claim` 走 `_accepted_fact_links`，任何非 ACCEPTED 支持事实被拒（探针：CANDIDATE 事实被拒）。
- 三类声明互斥：`ClaimVersion` 校验 `direct_evidence` 不得携带计算/AI 字段；`deterministic_calculation` 必须有可复算记录、计算输入必须等于支持事实、不得冒充 AI；`synthesis` 必须标识 `ai_disclosure_label_zh="AI 综合判断"` 且带方法。
- 计算保存输入/公式/结果：`DeterministicCalculationRecord` 强制 `result == round(input0-input1, 12)`，组间可比性（同指标/人群/时间/队列、单位一致且显式）在创建时校验；文字与复算结果直接矛盾（"-9.9" vs "-1.3"）被拒。
- AI 综合判断文字标识：`create_synthesis_claim` 强制文字以 `"AI 综合判断："` 开头，测试断言未标识被拒。
- Pydantic ↔ schema ↔ 清单：`schemas/{fact,claim}.schema.json` 的必填字段集与 Pydantic 模型逐字段对应，枚举值集合一致；两 schema 均在 `package-manifest.json` `components.schemas` 中登记；集成测试用 `Draft202012Validator + FormatChecker` 对 `model_dump(mode="json")` 实校验通过；`package verify` PACKAGE_OK。

## 缺陷

**P2-1｜JSON Schema 与 Pydantic 合同漂移（schema 更宽松）**：`fact.schema.json` 的 `allOf` 只编码了 `not_applicable`/`unresolved_due_to_route` 两个跨字段条件；timepoint 与 time_window 至少其一、reported 状态必须携带 `raw_value`、分子≤分母、`primary_fragment_id ∈ source_fragment_ids`、reported_zero 约束、规范化一致性均未进 schema。探针实测：timepoint/time_window 双 null 的文档 **schema 接受、Pydantic 拒绝**。外部仅依赖 schema 的消费者可写入非法事实。修复：在 schema `allOf` 补齐（至少时间必填项与 reported 状态 raw 非空两条）。

**P2-2｜对已规范化事实重复应用同一规则制造新版本标识**：`normalize_fact` 不拒绝 `fact.normalization is not None` 的输入。探针：对已规范化事实用同一规则再次规范化得到 `n1 ≠ n2`。ADR"重复应用同一规则不得制造新版本标识"仅在输入为原始事实时成立（测试覆盖的是该路径）。修复：输入已含同规则（同 rule_id+rule_version+同规范化值）记录时直接返回原版本或拒绝。

**P2-3｜计算声明文字校验是包含性而非矛盾性检查**：`create_deterministic_difference_claim` 只要求结果与单位是 claim_text 子串。探针："组间差为 -1.3 分，但手算为 -9.9 分。" **通过校验**。修复：解析文字中的候选数值，断言与 `result` 一致且无矛盾数值并存。

**P2-4｜事实版本标识包含工作流状态**：`extract_atomic_fact` 的版本负载含 `review_state`。探针：同科学内容、仅 review_state 不同（CANDIDATE vs ACCEPTED）抽取得到不同 `fact_version_id`，违反"事实标识由科学内容决定、不受工作流状态影响"。当前抽取路径恒为 CANDIDATE 故未触发。修复：从版本负载排除 `review_state`。

**P2-5｜声明合同约束仅在 capability 层**：`ClaimVersion` 模型本身不校验支持事实已接受、不校验 synthesis 文字前缀；探针确认可直接构造 `ClaimVersion` 链接 CANDIDATE 事实且通过模型校验。创建函数是当前唯一入口，故不构成实际绕行；建议将已接受校验与 AI 前缀校验下沉到 `ClaimVersion.model_validator`。

**P2-6｜非 reported 披露状态可携带值**：`NOT_REPORTED`/`NOT_PUBLICLY_DISCLOSED` 事实可带非空 `raw_value`（探针：raw="-2.1" 通过），"未报告"与数值并存语义矛盾，校验方向不对称（只要求 reported 必须有 raw，未禁止非 reported 带 raw）。修复需谨慎：允许"未报告该指标"类原文，但应禁止与状态矛盾的数值型 raw。

## Codex 仍需确认

- 上述 6 项 P2 是否在本任务内修复后复核，还是滚动到后续任务；P2-6 的修复边界（是否允许"未报告"类原文文本作为 raw_value）需业务判断。
- 事实入口的核验边界：本任务核验到"来源版本 ID 绑定 + 片段摘要 + 重开原文逐字一致 + raw==重开原文"；片段到来源版本**物理内容**（重读 source version 文件比对片段摘要）属 Task 2.6 IF 摄取层合同，本轮未发现缺口也未替其验收——是否补一条跨任务整合测试（fixture 从来源原文重开到声明）由 Codex 定夺。
- `FactDisclosureState.CONFLICTING` 状态存在但无强制约束要求该状态事实是冲突集成员（冲突语义目前由 `FactConflictSet` 承担）；如需该状态与冲突集强绑定，属后续增强而非本任务缺陷。
- 集成测试为合成数据 fixture，未冒充真实临床来源抽取质量；"Phase 2 fixture 可从来源原文重建实体—片段—事实—声明"的退出验收项（implement.md 中未勾选）仍需独立执行。

报告完成。未写入 runner 路径，本响应即交付。
