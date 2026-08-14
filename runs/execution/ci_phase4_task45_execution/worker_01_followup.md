合同补丁完成。补充报告如下：

---

# Execution Output: ci_phase4_task45_execution - worker_01 (follow-up)

## Boundary And Context Check

- 只读取 `context/ci_phase4_task45_execution_execution_context.md`、`src/ci_workflow/reports/common/evidence_view.py`、`tests/unit/reports/test_evidence_view.py`；未碰生产路径、JS/CSS/浏览器夹具，未装依赖，未切换模型，未另开会话。
- 只修改 Codex 指定的两个文件；`source_field_name` 是模型字段而非新公开类型，无需改动 `reports/common/__init__.py`，其 13 名导出合同不变。
- 现状确认：两文件仍为 untracked，内容与上一会话一致（25 项测试基线）。

## Work Performed

1. **测试先行（RED）**：先更新 fixture helper 拆出 `source_field_name`/`source_field_definition`，在缺失字段循环加入两字段，扩展 accept 断言，并新增精确失败测试 `test_extension_requires_separate_source_field_name_and_definition`（缺原名 → 拒绝；缺定义 → 拒绝；通用观察携带扩展字段 → 拒绝；`source_not_listed` 状态可用）。此时模型无该字段 → **RED：7 failed / 19 passed**，全部失败节点为 `source_field_name … Extra inputs are not permitted [type=extra_forbidden]` 及新断言不匹配——可观察失败节点成立。
2. **实现（GREEN）**：`_EXTENSION_FIELDS` 加入 `"source_field_name"`（置于 `source_field_definition` 之前）；`EvidenceView` 增加 `source_field_name: EvidenceField | None = None`。扩展字段族的必填/互斥逻辑由 `_extension_and_disclosure_integrity` 通过 `_EXTENSION_FIELDS` 自动生效，frozen/extra-forbid/披露一致性/页面 profile/固定集合合同均未触碰。
3. **过程缺陷自检修复**：三处编辑误吞了 `canonical_variable_family`（模型字段元组、fixture helper、缺失字段循环），一处 `**` 展开与关键字重复（TypeError），一处 strict-mypy union-attr 未收窄；均已修复并逐项复验（修复过程中 164 项曾显示 1 failed，即为该误吞的暴露点）。
4. **最终验证**：聚焦 26/26、reports 全量 164/164、scoped Ruff（check + format --check）与 strict mypy 全部通过。

## Artifacts And Evidence

| 路径 | 改动 |
|---|---|
| `src/ci_workflow/reports/common/evidence_view.py` | `_EXTENSION_FIELDS` 12 项（新增 `source_field_name`）；`EvidenceView` 新增 `source_field_name: EvidenceField | None` |
| `tests/unit/reports/test_evidence_view.py` | fixture helper 拆分原名/定义；缺失循环补 `source_field_name`；accept 断言两字段分别保留且不同（"Age" ≠ "入选时年龄（岁）"）；新增精确失败测试（含状态用例）；原有断言全部保留 |

- **RED**：`7 failed, 19 passed`（模型缺字段时，新节点全部可观察失败）。
- **GREEN**：
  - `uv run pytest tests/unit/reports/test_evidence_view.py -q` → **26 passed**
  - `uv run pytest tests/unit/reports -q` → **164 passed**
  - `uv run ruff check` → All checks passed；`ruff format --check` → 2 files already formatted
  - `uv run mypy <module> <test>`（in-tree）→ Success: no issues found in 2 source files

## Commands And Observations

```
uv run pytest tests/unit/reports/test_evidence_view.py -q   # RED: 7 failed, 19 passed → GREEN: 26 passed
uv run pytest tests/unit/reports -q                          # 164 passed
uv run ruff check/format --check <2 files>                   # clean
uv run mypy <2 files>                                        # clean (strict)
```

- 语义拆分达成设计意图：原名（如 `Age`，可逐字段保留英文原貌）与定义（中文定义文本）分列，跨试验核对可区分两者；两字段同为 `EvidenceField`，支持四态（新测试覆盖 `source_not_listed`），空白由既有 XOR/非空校验拒绝。
- `source_field_name` 未加入包级 `__all__`（非新类型），13 名公开导出合同未变，worker_02/03 的既有消费面不受影响——仅 baseline/disposition 扩展 payload 需多带一个必填字段。

## Blockers Or Missing Environment

无。uv/pytest/ruff/mypy 可用，全部检查按 Codex 指定的聚焦范围完成。

## Rerun Requests Or Next Step

无需重跑。Codex 如需进一步收紧，可考虑（均不属本次合同范围）：为 `source_field_name` 增加逐字保留说明（当前经 `EvidenceField` 空白折叠，与 `original_text` 的逐字保留不同）；在 renderer 合同测试（worker_02）中固定「来源原名/定义」的中文展示标签。
