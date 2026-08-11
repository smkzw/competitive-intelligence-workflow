All six original P2 items verified fixed; three residual defects confirmed with clean repros. Final report:

# Task 2.7 同 session 修复复核

**结论：FAIL** — 六项首轮 P2 均已修复并有反例测试覆盖，但复核发现 3 个新 P2（同规则内的残留不一致与一处误伤）。**P0=0, P1=0, P2=3**。

## 运行证据（全部真实执行，未修改任何文件）

| 命令 | 结果 |
|---|---|
| `uv run pytest tests/integration/test_source_to_claim_chain.py tests/integration/test_conflicts_preserved.py -q` | **4 passed** |
| `uv run pytest -q` | **182 passed** |
| `uv run ruff check src tests` | All checks passed |
| `uv run mypy --strict src` | Success, no issues (44 files) |
| `uv run ci-workflow package verify --root .` | **PACKAGE_OK** version=0.1.0a0 |
| `git diff --check` | exit=0 |

## 六项逐条结果

**P2-1 schema 跨字段规则与 Pydantic 一致性 — 修复，残留 2 处类型边界不一致（见新缺陷 P2-A/P2-B）**
schema `allOf` 已含四组机械规则：timepoint/time_window 至少其一（`anyOf`）、reported 状态必须 raw_value、`reported_zero` 必须零值原文证据 + numerator∈{0,null} + normalized_value∈{0,0.0,null}、`not_reported`/`not_publicly_disclosed` 否定数值型 pattern。Pydantic `_fact_contract_is_consistent` 逐条镜像。零值证据 pattern（`(?<![0-9.])0…` vs `(^|[^0-9.])0…`）与 not_reported 否定 pattern（锚定 fullmatch）语义等价。测试覆盖 missing-time、reported-without-raw、zero-contradiction、numeric-raw 四类反例。

**P2-2 规范化幂等 — PASS**
`normalize_fact`：同 rule_id+rule_version+同结果 → 直接返回原 fact（`repeated_on_normalized == normalized`，版本 id 不变）；同规则版本不同结果 → `ValueError("同一规范化规则版本不得产生不同结果")`；新规则版本 1.1 → 新 `fact_version_id`（链式 stable_id）且 `supersedes_fact_version_id` 指向旧版本。测试 `test_normalization_is_versioned_reversible_and_never_overwrites_raw_value` 全覆盖。

**P2-3 计算声明文字一致性 — 修复，残留 1 处误伤（见新缺陷 P2-C）**
错误结果（-9.9）与"正确结果+矛盾数值"（"-1.3 分，但手算为 -9.9 分"）均被 `ValueError("声明文字与复算结果不一致")` 拒绝；签名三值合法句"试验组为 -2.1 分，安慰剂组为 -0.8 分，组间差为 -1.3 分。"通过（我实测 ACCEPT）。stated_values 必须 ⊆ {treatment, control, result} 且 result 必须出现。

**P2-4 review_state 排除出版本身份 — PASS**
`extract_atomic_fact` 的 version_payload 显式 `exclude={"verified_fragment", "created_at", "review_state"}`；测试断言 `same_scientific_fact_after_review.fact_version_id == fact.fact_version_id`。

**P2-5 事实链接 accepted + synthesis 前缀 — PASS**
模型层：`ClaimFactLink.fact_review_state: Literal["accepted"]`，`_accepted_fact_links` 拒绝非 ACCEPTED 事实，`ClaimVersion._claim_kind_contract_is_explicit` 对 synthesis 强制 `startswith("AI 综合判断：")`（测试直接以 `ClaimVersion.model_validate` 验证模型层强制）；schema 层：`fact_review_state` const "accepted"，synthesis 分支 `claim_text` pattern `^AI 综合判断：`。测试覆盖 link 状态改为 candidate 的拒绝。

**P2-6 未报告状态数值原文 — PASS**
`not_reported`/`not_publicly_disclosed` + 数值型 raw（"-2.1 分"）→ `ValueError("不得携带数值型")`；"结果未报告"被 Pydantic 与 schema 双重接受（我实测 model=ACCEPT | schema=ACCEPT）。

## 新缺陷（P2，均附最小复现）

**P2-A — `reported_zero` 的 normalized_value 类型边界：Pydantic 放行 schema 拒绝**
最小复现：`AtomicFactVersion` 设 `disclosure_state=REPORTED_ZERO`、`raw_value="0"`、`normalized_value="0"`（str）或 `True`、附 matching `NormalizationRecord` → **model=ACCEPT，schema=REJECT**（`'0' is not one of [0, 0.0, None]`）。Pydantic 的零值检查仅作用于 `isinstance(normalized_value, (int,float)) and not bool`，str/bool 完全绕过。方向危险：Pydantic 校验通过的文件会挂在 schema 上。
最小修复：`_fact_contract_is_consistent` 中改为显式允许集——
```python
if isinstance(self.normalized_value, bool) or self.normalized_value not in (0, 0.0, None):
    raise ValueError("已报告零值的规范值必须为零")
```

**P2-B — 未报告数值型原文检测：Pydantic（Unicode `\d`）与 schema（ASCII `[0-9]`）不一致**
最小复现：`not_reported` + `raw_value="５０％"`（全角数字）→ **model=REJECT（正确），schema=ACCEPT**。Python `\d` 匹配 Unicode 十进制数字，JSON pattern 仅 `[0-9]`。方向安全（运行时更严），但 schema 作为序列化契约漏检。
最小修复：schema 两处数值 pattern 扩展为 `[0-9０-９]`（必要时含全角句点 `．`）。

**P2-C — 确定性计算声明误伤带方向词的幅度表述合法句子**
最小复现：treatment=-2.1、control=-0.8（单位"分"），claim_text=`"试验组下降 2.1 分，安慰剂组下降 0.8 分，组间差为 1.3 分。"` → **REJECT: 声明文字与复算结果不一致**。该句同时列示治疗组、对照组、组间差且方向词（下降）与数值符号自洽，正落在 P2-3"不误伤"验收范围内；规则把 +2.1/+0.8/+1.3 当作矛盾数值。
最小修复：`create_deterministic_difference_claim` 对不在 allowed_values 的 stated value，若其相反数在 allowed_values 且匹配 token 邻近文本含方向词（下降/减少/降低/升高/增加/高于/低于等），视为一致；该容忍不破坏现有反例（"-9.9 分"、"-1.3 分但手算为 -9.9 分"均非 ±allowed 或无数值方向词，仍拒绝）。

## 仍属后续阶段边界（不计缺陷）

- schema 无法表达跨文档约束，属设计内运行时强制：`calculation.input_fact_version_ids` ⊆ `supporting_fact_version_ids`、`fact_links` 与 `supporting_fact_version_ids` 顺序一致、声明生成时事实必须 ACCEPTED（`_accepted_fact_links`）。
- review_state 变更不产生新版本（正交于科学身份）为有意设计；review_state 仍是版本字段但被冻结模型约束。
- 冲突集合 `observed_values` 排序规范化（sorted）为确定性产物，不影响内容保真。

修复建议优先级：P2-A（方向危险，一行改动）> P2-C（验收范围内的误伤）> P2-B（schema 补漏）。
