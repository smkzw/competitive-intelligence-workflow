# Execution Output: ci_phase5_task52_execution - worker_03（第 5 轮 REVISE）

## Boundary And Context Check

- 直接修复当前工作树，未提交 Git、未进入模板/HTML/PDF/PPT/浏览器/安全测试。
- 修改文件（全部在允许范围）：
  - `src/ci_workflow/reports/a/pages.py`（P1-2 API、P1-3 结果绑定闭合、P1-4 唯一性）
  - `src/ci_workflow/capabilities/lineage_registry.py`（P1-1 摘要纳入完整来源版本）
  - `tests/unit/reports/a/**`（既有 10 个测试文件的构建器/权威签名升级 + `test_revise_round5_closure.py` 15 个反例回归）
  - 第 4 轮已改文件（contracts/__init__/snapshot_store/extraction_normalization/schema/contract store 测试）保持未动
- 读取路径仅限任务指定的强制文件与调用链相邻文件。

## Work Performed（按 P1-1…P1-4 逐项）

**P1-1 完整来源版本进入科学证据摘要**：`compute_scientific_content_digest` 从「fragment 字段 + source_version_id」升级为每个 `VerifiedEvidenceFragment` 的完整规范序列化：完整 `fragment`（含定位/原文/摘要/时间）、完整 `source_version`（含 source_id、content_sha256、content_relative_path、media_type、获取/发布/生效/首次披露日期、acquired_locator）、`reopened_original_text`；事实仍完整纳入；稳定排序（fragment_id / fact_version_id）不变；写入（工厂）与验证（`_assert_evidence_context_bound` 重算比对）共用。RED：回退摘要字段 → 5 个 source_version 篡改参数（content_sha256/路径/acquired_at/media_type/source_id）全部 `DID NOT RAISE`（5 failed）。正向 `digest1 == digest2 == manifest`、改 reopened 原文改变摘要。

**P1-2 当前合同权威移到 `AEvidenceContext` 之外**：`_assert_evidence_context_bound` 增加外部必填参数 `authoritative_contract_store: ProjectContractStore`；8 个 `build_*_view` 与 8 个 `assert_*_authoritative` 全部新增必填关键字参数（无默认值，`inspect` 断言覆盖），权威校验只能从外部参数重载当前合同；`AEvidenceContext.contract_store` 保留为非权威信息并强制与外部权威存储身份一致（project_root 比对），不一致拒绝。RED：回退为信任 context 内 store → 全套自洽伪造（合同/清单/锁定/内容寻址/宇宙快照/context contract_store 全替换为 999/2099，仅外部权威 store 保持原始）`DID NOT RAISE`。正向外部 store 通过、8 权威入口重建一致。

**P1-3 结果绑定闭合产品、试验与来源血统**：`_assert_result_binding_matches_fact` 新增：`fact.entity_id == binding.object_id`、`binding.source_location` 精确等于主片段 locator 稳定渲染、`source_role`/`review_state`/`disclosure_state`/`disclosure_maturity` 与事实一致；dossier 循环传入片段定位并在校验通过后才消费。RED：分别禁用实体/定位/来源角色检查 → 跨产品复制绑定（保留原绑定、副本改 binding_id）、伪造 source_location、伪造 source_role 三个用例均 `DID NOT RAISE`（3 failed）。修复测试为「复制」而非「移动」绑定（移动会先破坏原产品锚定，无法命中本层校验）；副本携带独立 binding_id（否则先被 P1-4 拒绝）。

**P1-4 结果事实和绑定唯一消费**：`_revalidate_inputs` 强制全部传入 `binding_id` 全局唯一；dossier 循环按 (产品, 结果事实版本) 维护唯一集合（同一事实经复制绑定渲染两次、或以疗效/安全冲突域出现均失败关闭）。RED：同时禁用两处检查 → 重复 binding_id 与重复结果事实两个用例均 `DID NOT RAISE`（2 failed）。正向疗效/安全各一条保持唯一通过。

## Artifacts And Evidence

- `tests/unit/reports/a/test_revise_round5_closure.py`：15 个反例回归（P1-1×6、P1-2×3、P1-3×3、P1-4×2 + 正向）全 GREEN。
- 既有 10 个测试文件：所有 build/authority 调用补 `authoritative_contract_store=<evidence>.contract_store`（含多行/星号/位置参数顺序修复）、签名断言补参。
- RED 证据（故障注入逐项，均 failed 后恢复，`pages.py`/`lineage_registry.py` 与备份逐字节一致）：P1-1×5、P1-2、P1-3×3、P1-4×2。

## Commands And Observations

```
uv run pytest tests/unit/reports/a -q                                 → 219 passed
uv run pytest tests/reports/a tests/unit/reports/a -q                 → 310 passed
uv run pytest tests/unit/test_gate_evaluator.py tests/reports/test_report_specific_gates.py \
  tests/reports/test_gate_override_strictness.py tests/integration/test_no_draft_when_blocked.py \
  tests/reports/a tests/unit/reports/a -q                             → 527 passed
uv run pytest tests/unit/test_project_contract_store.py tests/integration/test_snapshot_identity.py \
  tests/contract -q                                                   → 110 passed
uv run pytest tests -q --ignore=tests/browser --ignore=tests/acceptance → 1047 passed
uv run ruff check src/ci_workflow/reports/a src/ci_workflow/capabilities src/ci_workflow/storage \
  tests/unit/reports/a tests/unit/test_project_contract_store.py tests/integration/test_snapshot_identity.py \
  tests/reports/a                                                    → All checks passed!
uv run mypy --strict src                                              → Success: no issues found in 89 source files
```
第 4 轮 38 个攻击测试保持全通过（未弱化）。

## Blockers Or Missing Environment

无环境阻塞。残余问题（供 Codex 裁决）：
- P1-2 的「外部权威 store」由调用方显式传入；若工程已有项目数据库服务，可替换读取器而不改视图边界（与第 4 轮结论一致）。
- P1-3 的来源角色比较基于 `fact.source_role`（字符串）与 `binding.source_role.value`；若事实来源角色词表扩展需同步。
- P1-4 的 binding_id 唯一性为全局强制；若未来允许跨报告复用绑定 ID 需改为按报告作用域（当前 A 报告单一作用域，无冲突）。

## Rerun Requests Or Next Step

- 未自行宣告验收、未提交。建议 Codex：复核 P1-2 外部权威注入 API 与 P1-1 摘要完整性后接受；可提交本轮修改并推进 Task 5.3。若需把外部权威 store 接入既有项目存储服务或调整绑定 ID 作用域，请提供对应输入源。
