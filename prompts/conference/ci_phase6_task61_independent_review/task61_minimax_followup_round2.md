Delegated mode. Conference participant. 你是原 Task 6.1 同一 Pi→MiniMax 审阅会话。上一轮你把关键 III 期的亚组/事后证据判为核心，Codex 根据已批准设计裁定该解释错误：母试验可为核心，但延伸、亚组、事后和真实世界结果本身只能进入支持层。本轮只复核最终修复。

## Hard boundaries

- 只读审阅，不修改文件、不安装依赖、不对外通信、不声称最终产品放行。
- Read these files only: `src/ci_workflow/reports/common/study_roles.py`, `policies/studies/study-role-v1.yaml`, `tests/reports/test_study_role_policy.py`。
- Runner-managed report path: `runs/conference/ci_phase6_task61_independent_review/task61_minimax_followup_round2.md`。不得用工具写此文件，只在最终回复返回完整审阅结果。

当前修复：B/C 核心与特殊核心规则均限定 `evidence_types: [standard]`；关键 III 期的 extension/subgroup/post_hoc/real_world 四类结果必须为 supporting；策略加载器拒绝相同结构适用范围却分配不同角色的规则。Codex 已运行 34 项定向测试和 986 项跨 A/B、PubMed、ClinicalTrials.gov 回归，均通过。

请实际重放上述四类关键 III 期探针和冲突规则探针。输出中文原生的 `PASS` 或 `FAIL`；若 FAIL，只列仍可复现的错误纳入或规则冲突绕过。
