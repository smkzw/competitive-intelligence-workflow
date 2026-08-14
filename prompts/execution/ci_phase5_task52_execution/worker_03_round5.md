# 第 5.2 步同会话修复第 5 轮

继续原 worker_03 会话。Luna 第 4 轮独立复核为 `REVISE`，完整报告：
`runs/conference/ci_phase5_task52_verify/luna_verifier_round4.md`。

## Hard boundaries

- 仅在当前工作区修复，不提交 Git，不进入模板/HTML/PDF/PPT/浏览器/安全测试。
- Read these files only as initial set: `AGENTS.md`、Luna round4 报告、round4 实现与精确测试；仅沿这四项修复的调用链读取相邻文件。
- Runner 管理唯一输出文件，Agent 不自行写入。

Read these files only:
- `AGENTS.md`
- `runs/conference/ci_phase5_task52_verify/luna_verifier_round4.md`
- `src/ci_workflow/reports/a/pages.py`
- `src/ci_workflow/storage/project_contract_store.py`
- `src/ci_workflow/capabilities/lineage_registry.py`
- `tests/unit/reports/a/test_revise_round4_closure.py`

Exact writable files:
- `src/ci_workflow/reports/a/pages.py`
- `src/ci_workflow/reports/a/contracts.py`
- `src/ci_workflow/reports/a/__init__.py`
- `src/ci_workflow/capabilities/lineage_registry.py`
- `src/ci_workflow/storage/project_contract_store.py`
- `tests/unit/reports/a/`
- `tests/unit/test_project_contract_store.py`
- 与公共调用签名变化直接相关的 A 类测试文件

Runner-managed report path: `runs/execution/ci_phase5_task52_execution/worker_03_round5.md`.

先把以下四个 Luna 原始攻击转成测试，确认当前实现 RED，再修复。

## P1-1 完整来源版本进入科学证据摘要

- `compute_scientific_content_digest` 不得只取 fragment + source_version_id。对每个 `VerifiedEvidenceFragment` 纳入完整、重验证后的规范序列化内容，至少完整 `fragment`、完整 `source_version`、`reopened_original_text`；事实仍完整纳入。
- 仅改 `source_version.source_id/content_sha256/content_relative_path/acquired_at` 或其他日期/状态/定位字段，保留所有 ID 和 manifest 时必须因摘要不匹配拒绝。
- 写入与验证共用一个实现，稳定排序，正向不漂移。

## P1-2 把当前合同权威移到 `AEvidenceContext` 之外

- 不能继续信任 `evidence.contract_store`。为所有 8 个公共 `build_*_view` 与 8 个 `assert_*_authoritative` 入口增加独立、显式、关键字参数，例如 `authoritative_contract_store: ProjectContractStore`（或等价只读 handle）；所有权威校验只能从该外部参数重载当前合同。
- `AEvidenceContext.contract_store` 可删除，或保留仅作非权威信息但绝不能参与信任决定。公共入口必须比较 context/manifest/locked 中合同与外部权威 store 当前合同，并校验项目身份。
- Luna 的全套伪造攻击会替换 context、manifest、locked snapshot、snapshot store、context 内 contract store，但继续传原始外部权威 store；必须拒绝。正向统一传真实外部 store。
- 这是纯函数/应用边界的信任注入：无需宣称 Python 参数不可伪造，但 API 必须清楚区分“不可信报告上下文”和“应用层权威合同源”。所有测试/导出同步更新，不留兼容默认值绕过。

## P1-3 结果绑定闭合产品、试验与来源血统

- 对疗效/安全结果 binding 强制：
  - `fact.entity_id == binding.object_id`（当前 A 结果事实实体是产品）；
  - binding.trial_id 属于该产品且与当前锚定试验一致；
  - binding.source_location 精确等于事实主片段 locator 的稳定渲染；
  - binding.source_role、review_state、disclosure_state、disclosure_maturity 与已接受事实一致；必要时同时检查 conflict disposition。
- Luna 攻击：把度普利尤单抗的 `fact-v-1/v-2` 复制绑定到 `p-clinical/NCT-clin-1` 并给其增加锚定试验，必须拒绝。仅伪造 source_location 或 source_role 也必须拒绝。
- 后续摘要只消费重验证且已闭合的 binding。

## P1-4 结果事实和绑定唯一消费

- 所有传入 binding_id 全局唯一；重复 ID 失败关闭。
- 对每个产品、结果域维护 fact_version_id 唯一集合；同一结果事实不能因复制 binding_id 而渲染两次。若同一事实同时以疗效与安全冲突域出现也失败关闭。
- Luna 攻击复制 `b-eff` 仅改 `binding_id`，必须拒绝；正向疗效/安全各一条保持通过。

## 验证

1. 新增四类攻击的 RED/GREEN 精确结果。
2. `uv run pytest tests/unit/reports/a -q`
3. `uv run pytest tests/reports/a tests/unit/reports/a -q`
4. 共享 gate/no-draft/A 组合。
5. 相关 snapshot/contract/store tests。
6. 目标 Ruff；`uv run mypy --strict src`。
7. 非 browser/acceptance 全库。

不得弱化第 4 轮已通过的 38 个攻击。不要自行宣告验收，不提交；最终交接逐项列机制、RED/GREEN、精确命令和残余问题。

Output file: `runs/execution/ci_phase5_task52_execution/worker_03_round5.md`
