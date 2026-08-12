# Conference Participant Output: ci_phase3_task32_final_audit01 - general_pi_qwen38

**VERDICT: PASS (P0=0, P1=0)**

## Boundary Check

- 同一 verifier 会话续跑；只读审查，未修改任何源/测试/schema/Trellis/验收记录（`git status` 仅含既有 Task 3.2 未提交变更，实验脚本全部在 `/tmp`，仓库无新改动）。
- 未读取其他验收者输出、`runs/conference/ci_phase3_task32_audit01/`、`runs/execution/` 或 worker 推理。
- 已核对本次 delta：`git diff` 七文件（exhaustion.py、blocker_audit.py、schema、四份测试）相对上一轮的具体变化，并重读了全部关键 validator。

## Independent Work Product

**机械复测（独立复现）：**

| 检查 | 命令 | 结果 |
|---|---|---|
| Task 3.2 四文件精确套件 | `uv run pytest tests/integration/test_double_exhaustion.py tests/integration/test_no_draft_when_blocked.py tests/integration/test_no_draft_on_unresolved_key_conflict.py tests/integration/test_no_draft_after_scientific_qc_rejection.py -q` | **98 passed** (3.70s) |
| Task 3.1 回归 | `uv run pytest tests/unit/test_gate_evaluator.py tests/reports/test_report_specific_gates.py tests/reports/test_gate_override_strictness.py -q` | **143 passed** |
| 全库 | `uv run pytest tests/ -q` | **429 passed** |
| Ruff（7 差异文件） | `uv run ruff check …` | clean |
| strict mypy | `uv run mypy src` | Success (51 files) |
| `git diff --check` / schema | | clean / Draft202012 可校验 |

**五项 delta 逐一验证（代码审查 + 复现/反例）：**

1. **每适用路线恰一条摘要，一条摘要可含多条回执** — `exhaustion.py:485-496` `_applicable_routes_and_receipts_are_bound` 新增 `len(route_evidence) != len(applicable_route_ids)` 拒绝；route_ids 集合一致 + 跨路线回执互不相交保留。攻击 CE-NEW1（同一 route_id 重复摘要行、重算复核摘要）→ **REJECTED**「每个适用路线必须恰有一条路线摘要：摘要数=2 适用路线数=1」。单条摘要内多条回执合法（attempt_count=len(receipt_ids)、access_methods 派生）。新测试 `test_duplicate_route_summary_rejected`。
2. **终末结果类别由实际回执确定性派生** — `exhaustion.py:93-110` `derive_terminal_result_class`（按 `(ended_at, receipt_id)` 取终末回执的 result_class）；`exhaustion.py:652-687` `_assert_route_derived_from_receipts` 新增派生比对与「ACCESS_BLOCKED 必须终末为技术类别」检查。攻击重放：CE1（not_found 回执 + content_acquired 声明）→ **REJECTED**「声明=content_acquired 派生=not_found」；CE5（技术缺口全部 content_acquired 回执 + rate_limited 声明）→ **REJECTED**。合法科学 content_acquired：构造两轮饱和证明、轮 2 终末回执 content_acquired 且绑定不可变来源版本 → **ACCEPTED**（`/tmp/ce_positive.py`；对应新测试 `test_scientific_final_class_must_derive_from_receipts` 双向断言）。技术访问阻断 + 成功终末 → **REJECTED**（`test_technical_access_blocked_route_rejects_successful_terminal`）。
3. **空场景证据恰一个资格缺口、绑定检索范围、科学缺失状态** — `blocker_audit.py:292-309`：`len(gaps)==1`、`gap.object_id == search_scope_id`（scope 必填）、`current_state in SCIENCE_ABSENT_STATES`。攻击 CE3b（第二资格缺口、独立回执 ID）→ **REJECTED**「空场景证据必须恰有一个资格穷尽缺口」。新测试 `test_empty_evidence_requires_exactly_one_gap_with_scope_object`（含对象冒充产品/试验拒绝）。
4. **空路径公共写入口绑定真实 GateSpec 标识与资格字段** — `blocker_audit.py:1187-1199`：`evidence_gap.gate_spec_id == spec.spec_id`、`evidence_gap.field_id == eligibility_gate_unit_id()`。攻击 CE-NEW2（摘要一致构造跨 spec `gate-spec-b-v1` / 错字段 `a_product_identity`）→ 模型层接受（无 spec 上下文）、**公共写入口 REJECTED**「空场景资格缺口锚点必须绑定真实 GateSpec 说明书标识」/「…字段必须等于资格单元字段」，且 `blockers/` 不存在。新测试 `test_empty_path_rejects_cross_report_gate_spec_and_wrong_field`（A/B/C 全覆盖）。
5. **B/C 空必绑闭合快照，A 真零产品免快照** — `blocker_audit.py:1126-1140`：B/C `snapshot is None → raise`，且候选产品/试验必须与快照完全一致；A 仍禁止非空快照。攻击 CE4（B 空不带 snapshot）→ **REJECTED**「B/C 空场景必须绑定闭合宇宙快照」。新测试 `test_bc_empty_requires_closed_snapshot_but_a_true_zero_allows_none`（B/C 拒绝 + A 真零通过）。

**既有攻击面回归（全部重放）：** CE1/CE1b/CE5/CE3b/CE4 已在上表；CE2 仍 ACCEPTED（见 P2）；GateSpec 参数化 31 单元矩阵、空 3 场景、冲突 3、QC 3 计数不变（40 参数化场景，collect-only 核对）；`test_nonempty_candidate_blocked_only_on_one_critical_unit` 的 31 例全部通过且每个用例阻断集恰为该单元。

## Evidence And Assumptions

- 本轮的 P1（路线摘要终末类别伪造）经实现修复，且修复未过杀合法科学 content_acquired（正例独立构造通过，负例拒绝）；duplicate-route 与 cross-spec 空场景两个新攻击面均被机械拒绝。
- [INFERENCE] `final_result_class` 现由 `(ended_at, receipt_id)` 终端规则派生；回执时间序在 `SamePathRetryAudit`/`RecoveryRound` 验证器约束下与尝试序一致，故该派生与 attempt_index 序等价且确定性成立（未发现反例）。

**剩余 P2（非阻断，均不改变结论）：**

1. **CE2** — `src/ci_workflow/sources/retries.py:385-405`：`SamePathRetryAudit` 回执不要求属于恢复历史（替代路径回执有 `alternative_receipt_ids <= history_receipt_ids` 于 `:383`），附加不在历史中的重试回执仍被接受，可放大路线尝试计数（用户 Markdown「累计完成 N 次尝试」）。`retries.py` 不在本轮七文件变更集内，未修复。建议：要求重试审计回执 ⊆ 恢复历史回执。
2. 跨缺口回执 ID 可重名（仅按 gap 作用域唯一）。
3. 同一 `audit_id` 内容漂移抛错后，同版本重跑需人工删除既有阻断目录（设计决策，操作摩擦）。
4. `_build_blocker_audit` 无法从证据绑定重推导阻断集合（诚实调用方边界；建议 Task 3.4 图层传入评估摘要）。
5. `apply_scientific_qc_rejection` 对已穷尽记录未执行宇宙关系图实体绑定。

## Risks, Gaps, And Verification Needs

- P2-1 是审计完整性最接近 P1 的项；若后续回合将 `retries.py` 纳入变更，应补 `test_*` 断言重试回执必须进入历史，并回归 `test_mixed_gaps_via_full_production_path`（技术路线 attempt 计数 5 的既有断言）。
- 未覆盖验证面：真实 Graph 执行器（Task 3.4）只把真实 `evaluate_report` 结果传入公共入口；`blockers/<report>/<version>/` 与事件日志在真实工作区的一致性（超出本任务范围）。

## Recommended Next Step

Codex 接受本 PASS 并将 P2-1 作为下轮（Task 3.3/3.4 批次）的可选加固项；修复 P2-1 时同步补重试回执入历史的回归测试。P0=0、P1=0，精确测试 98/143/429 与全部独立反例验证通过。
