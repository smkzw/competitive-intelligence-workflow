# 第 5.2 步独立验收第 5 轮

继续原 Luna 会话，只读验收。执行交接：`runs/execution/ci_phase5_task52_execution/worker_03_round5.md`；上一轮结论：`runs/conference/ci_phase5_task52_verify/luna_verifier_round4.md`。

## Hard boundaries

- 不修改工作树，不提交，不做模板/HTML/PDF/PPT/浏览器/安全测试。
- Read these files only as initial set: 上述两份报告、当前四项修复源码与 `test_revise_round5_closure.py`；必要时沿验证调用链只读相邻文件。
- 不接受执行者自报；独立运行原始四个攻击和机械检查。

Read these files only:
- `runs/conference/ci_phase5_task52_verify/luna_verifier_round4.md`
- `runs/execution/ci_phase5_task52_execution/worker_03_round5.md`
- `src/ci_workflow/reports/a/pages.py`
- `src/ci_workflow/capabilities/lineage_registry.py`
- `tests/unit/reports/a/test_revise_round5_closure.py`

Runner-managed report path: `runs/conference/ci_phase5_task52_verify/luna_verifier_round5.md`.

请重点重放：

1. 仅改完整 `SourceVersionRecord` 的 source_id/content_sha256/path/acquired_at/media_type/日期状态或 reopened text，锁定 manifest 不变，所有入口应拒绝；正向摘要确定。
2. context、context contract_store、contract、manifest、locked snapshot、snapshot store、universe snapshot 全部自洽改 999/2099，但仍传原外部 `authoritative_contract_store`，8 个 build/authority 应拒绝；确认外部参数必填且无默认绕过。
3. 复制度普利尤单抗结果 binding 到另一产品/试验并增锚定试验；伪造 source_location/source_role/review/disclosure；都应拒绝。核实 fact.entity_id、试验归属和主片段 locator 真正闭合。
4. 重复 binding_id、复制 binding 仅改 ID 复用同一 fact、跨疗效/安全域复用同一 fact，应拒绝；正向无重复。
5. 重跑 round4 38 项、round5 15 项、A 单元、目标 Ruff、strict mypy；确认没有弱化 no-draft 和中文展示。

最终仅 `PASS` 或 `REVISE`。PASS 要求 P0=0、P1=0，四个攻击全拒绝且机械检查通过。若 REVISE，给符号、构造、实际、预期和最小修复。全程只读。

Output file: `runs/conference/ci_phase5_task52_verify/luna_verifier_round5.md`
