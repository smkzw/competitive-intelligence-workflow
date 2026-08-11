# Codex Review: ci_phase2_task22_identity

Date: 2026-08-11
Delegated-agent output: `runs/pi_ci_phase2_task22_identity.md`

## Verdict

PASS。Task 2.2 可以接受；Task 2.3 及后续能力未提前接受。

## Boundary Check

- 独立 reviewer 使用夜间有效路由 `Pi/opencode-go/deepseek-v4-flash:max`，session `019ff143-b659-7000-ad51-77680e15f60d`；修复后通过同一 session 复核，`resume_session_reset=false`，无 fallback。
- Reviewer 全程只读，runner 仅写其管理的报告与原始输出。Reviewer 为核对 `stable_id` 额外读取了项目内的直接依赖 `src/ci_workflow/domain/ids.py`，超出提示文件的枚举但未超出工作区、任务原因或权限；没有修改产品文件。

## Codex Verification

- Codex 修复后逐项运行三个新增节点：身份依据守卫、适格记录一一对应、待审查阻断，均为 `1 passed`；Task 2.2 共 10 passed，全库 147 passed。
- `ruff check src tests`、strict mypy（27 个源文件）、`package verify --root .` 和 `git diff --check` 通过。
- 代码检查确认内部 ID 由实体类型与独立身份依据生成；名称、别名和登记号不能直接作为依据；NCT/CTR 是可冲突、可追溯的外部标识。
- 适格记录与实体双向一一对应；重复、漏评、未知引用均拒绝；pending 阻止闭合；150 实体无排序或切片。
- 当前步骤无用户界面或报告产物，因此不适用浏览器/PPT/PDF/视觉验收。

## Delegated-Agent Output Review

Hermes 首次独立验收为 FAIL，P0=0、P1=2，并准确发现重复适格与漏评实体两条静默完整性问题；修复后同 session 返回 PASS，P0/P1/P2 均为 0。其最终报告有一处叙述误差：称三个新增节点都有真实 RED，但 `pending` 节点首次即通过；Codex 已在 `docs/acceptance/runs/task-2.2/red.txt` 与最终 verdict 中纠正。该误差不影响实现行为、真实测试数或两项 P1 的闭合证据。

## Residual Risk

- 全部排除时宇宙可以闭合但为空；“闭合且非空”由后续 GateSpec 求值器承接，必须在 Task 2.3 之后的相应实现中机械验证。
- 跨来源 `identity_basis` 的派生规则仍需在摄取合同中固定；本步只保证名称、别名和登记号不能被直接滥用。
