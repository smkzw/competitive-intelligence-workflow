Delegated mode. Conference participant. 你是原 Task 6.1 同一 Grok Build/grok-4.6（medium）审阅会话。本轮只复核你刚指出的两个阻断是否闭合。

## Hard boundaries

- 只读审阅，不修改文件、不安装依赖、不对外通信、不声称最终产品放行。
- Read these files only: `src/ci_workflow/reports/common/study_roles.py`, `policies/studies/study-role-v1.yaml`, `tests/reports/test_study_role_policy.py`。
- Runner-managed report path: `runs/conference/ci_phase6_task61_independent_review/task61_grok_followup_round2.md`。不得用工具写此文件，只在最终回复返回完整审阅结果。

Codex 已裁定延伸、亚组、事后和真实世界结果只进入支持层，母试验的标准证据才可进入核心层。当前修复为：所有 B/C 核心与特殊核心规则显式限定 `evidence_types: [standard]`；新增关键 III 期四种 contextual evidence 均必须为 supporting 的参数化测试；策略加载器对相同结构适用范围却分配不同角色的规则拒绝加载。指定三文件现为 34 项通过，Ruff、strict mypy 与差异检查通过。

请重放：关键 III 期 + extension/subgroup/post_hoc/real_world；以及克隆核心适用范围、改为 supporting 并提高优先级。输出中文原生的 `PASS` 或 `FAIL`。若 FAIL，只列这两个阻断仍可实际绕过的精确证据。
