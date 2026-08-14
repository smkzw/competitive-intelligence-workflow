# 第 5.2 步独立复核第 2 轮

请继续你上一轮的独立验证会话，保持验证者身份，只读审查当前工作树，不修改文件。上一轮指出的 8 类问题已由原执行会话修复，执行报告位于：

- `runs/execution/ci_phase5_task52_execution/worker_03_round2.md`
- 新增反例：`tests/unit/reports/a/test_revise_closure.py`
- 当前生产实现：`src/ci_workflow/reports/a/pages.py`、`contracts.py`、`analysis.py`

Codex 已独立复跑：`tests/unit/reports/a` 110 passed；`tests/reports/a + tests/unit/reports/a` 201 passed；目标 Ruff 与 strict mypy 均通过。测试绿不是接受证据，请重新从攻击者/真实调用链角度构造最小反例。

## 必须复核

1. 你上一轮的 AV04—AV08 假 fact/locator、换 evidence_snapshot_id、伪 analysis/model_copy、监管事件重复配对、历史状态矛盾、程序员标签泄漏、空/残缺 DTO、伪 AProjectContract 是否真实失败关闭。
2. `AEvidenceContext.locked` 是否真的与 `manifest` 内容摘要、snapshot_id、relative_path、byte_size 重新核对；如果只是比较 ID 而不校验 locked 对 manifest 的内容寻址身份，请给可运行反例。
3. `EvidenceSnapshotManifest.contract_version/data_cutoff` 是否与当前权威 `ProjectContract` 绑定；若调用边界没有当前合同，判断这是第 5.2 必须修复还是可明确延后，并说明理由。
4. 页面记录的展示值是否与被引用 `AtomicFactVersion.raw_value/normalized_value` 一致。尝试在保持 project_id/field_id/locator/fact_version_id 不变时篡改 region/phase/status、监管日期、企业名称/交易条款、专利日期/状态、历史状态说明，判断能否通过。
5. `ScientificLineageRegistry`、`ApplicableUniverseSnapshot`、`AProjectContract`、`GateEvidenceBinding` 通过 `model_copy` / `model_construct` 绕过验证后，公开构建器是否会重新 `model_validate`，还是只检查部分派生关系。
6. “完整产品档案”是否真的包含 AV04—AV08 全维度和结果承载产品的疗效/安全性强类型摘要；是否能通过漏记录或重复记录获得貌似完整的档案。
7. 临床组合对非核心但适格研究角色的处理是否符合规格，而非把 `EARLY_DECISION` 简单映射成“其他适格”后允许自由分类；默认排除研究是否仍可能进入。
8. 用户可见文本校验是否误伤合理英文药名/靶点/NCT/机构，也是否遗漏大小写、Unicode、标点拆分、`Gate`/`backend-state` 等工程词变体。

## 输出

返回 `PASS` 或 `REVISE`。仅列可复现、与第 5.2 目标直接相关的问题，按 P0/P1/P2 排序。每项给：文件/符号、最小构造、实际结果、预期结果、为何现有测试未捕获。若 PASS，明确列出你实际执行的反例及其拒绝结果。不要修改工作树，不要凭代码阅读直接推断通过。
