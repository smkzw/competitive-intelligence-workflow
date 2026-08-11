六项机械检查全部真实通过；8 个文件 mtime 与上轮一致、无新变更，上轮本会话内真实运行的对抗探查输出（同一只读会话）与测试新增断言构成四点证据。复核报告如下（不写 runner 报告路径，由 runner 持久化）。

---

# Task 2.4 同 session 修复复核

## 结论

**PASS** — P0=0，P1=0，P2=0；三项原 P2 均已关闭，修复未引入新缺陷。

依据：8 个文件 mtime（23:40:54–23:42:34）与上轮逐行核对时刻完全一致，无新变更；六项机械检查本轮真实重跑通过；对抗探查输出为本会话上轮真实运行且代码未变，仍有效。

## 四点逐项证据

**1. `trial_design` 白名单** ✓
- `pubmed.py:assess_key_field_coverage`：`trial_design` 仅接受 `{"clinical_trial_registry", "regulatory_material"}`，其余（含 `primary_publication`、`supplementary_material`）进 `rejected_contributions`，rationale 明确"论文及其补充材料可用于结果交叉核验，但不能替代登记平台或监管材料中的方案字段"。
- 测试：`test_pubmed_cross_reference.py` 二测新增 supplement-only 分支断言 `supplement_state == "required"`、`accepted_contributions == ()`、rationale 含"方案字段"；既有断言 `primary_publication` 方案字段被拒、论文-only 时 `design.eligibility_criteria` 在 missing。
- 独立探查（本会话）：仅 `supplementary_material` 贡献 → `("required", ["design.eligibility_criteria"], 0)`；`regulatory_material` → `not_required`（无过度拒绝）。

**2. 指南谱系校验** ✓
- `regulators.py:validate_guideline_lineage`：① 每系列 `can_drive_current_default` 至多一个（"同一指南系列存在多个当前版本"）；② 沿 `superseded_by` 链 DFS 环检测（"指南替代关系存在循环"）；既有悬空/单向/双向一致检查保留。
- `select_current_guideline_basis` 函数体首行即 `validate_guideline_lineage(guidelines)`，任何入口均不能绕过谱系校验。
- 测试：`test_regulators.py` 新增 `pytest.raises(ValueError, match="多个当前版本")` 与 `match="循环"` 两个对抗用例；合法链 `select_current_guideline_basis(...) == (new_final,)` 保持通过。
- 独立探查：3 循环 → 抛"指南替代关系存在循环"；同系列双 active final → 抛"同一指南系列存在多个当前版本"；合法 old→new 链 → 恰选最新 final。

**3. 缺 citation 的引用边** ✓
- `clinicaltrials_gov.py:PublicationCrossReference` 新增 `citation: str | None` + `citation_state: Literal["reported","not_publicly_disclosed"]`；`create_publication_cross_references` 对无/空白 citation 保留边并置 `not_publicly_disclosed`。
- `_citation_state_matches_value` 双向强制：`reported` 必须有值、`not_publicly_disclosed` 不得有值——状态与值不可不一致。
- 测试：`test_ctgov.py` 三测新增无 citation 引用 `{"pmid": "40000009", "type": "DERIVED"}`，断言边保留、`citation is None`、`citation_state == "not_publicly_disclosed"`，且三边列表/类型断言同步更新。
- 独立探查：`(None, "not_publicly_disclosed")`，不再整页失败。

**4. 三项 P2 关闭且无新缺陷** ✓
- P2-1（补充材料覆盖方案字段）→ 已关闭：白名单 + 测试 + 探查三方确认。
- P2-2（替代环）→ 已关闭：DFS 环检测 + 测试 + 探查确认。
- P2-3（同系列多当前版本）→ 已关闭：每系列唯一当前 + select 前置校验 + 测试 + 探查确认。
- 修复未引入 P0/P1/新 P2：全库 166 通过、strict mypy 37 文件无问题、ruff 通过、`package verify` PACKAGE_OK、`git diff --check` 通过；`regulatory_material` 覆盖方案字段、合法替代链、带引文 reported 状态均未遭误伤。

## 运行证据

| 检查 | 真实输出 |
|---|---|
| 组合（7 项） | `7 passed in 0.06s` |
| 全库 | `166 passed in 6.12s` |
| `ruff check src tests` | `All checks passed!` |
| `mypy --strict`（37 源文件+3 测试） | `Success: no issues found in 37 source files` |
| `package verify --root .` | `PACKAGE_OK version=0.1.0a0 stage=phase-0-task-0.4` |
| `git diff --check` | `DIFF_CHECK_OK` |

## 仍需修复项

无。遗留观察仅两条（非缺陷）：① `EvidenceContribution` 与 `ClassifiedPublication.role` 的接线在 Task 2.7，需用 `can_replace_primary_report` 门控；② `select_current_guideline_basis` 现对传入集合内任何非法谱系抛错，Task 2.7 接线须传完整一致集合。均不属本任务修复范围。
