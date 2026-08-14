# Execution Output: ci_phase5_task52_execution - worker_03（第 4 轮 REVISE）

## Boundary And Context Check

- 直接修复当前工作树，未提交 Git、未进入模板/HTML/PDF/PPT/浏览器/安全测试。
- 修改文件（全部在允许范围）：
  - `src/ci_workflow/storage/snapshot_store.py`（`EvidenceSnapshotManifest.scientific_content_digest`）
  - `src/ci_workflow/storage/project_contract_store.py`（新增：权威当前合同只读存储）
  - `src/ci_workflow/capabilities/lineage_registry.py`（`compute_scientific_content_digest`、`from_state` 公开重建）
  - `src/ci_workflow/capabilities/extraction_normalization.py`（`revalidate_verified_fragment`）
  - `src/ci_workflow/reports/a/pages.py`（P1-1…P1-4、P2-5、P2-6）
  - `src/ci_workflow/reports/a/contracts.py`、`__init__.py`（仅导出）
  - `schemas/evidence-snapshot-manifest.schema.json`（清单摘要字段）
  - `tests/unit/reports/a/**`（夹具升级 + `test_revise_round4_closure.py` 38 个反例回归）
  - `tests/unit/test_project_contract_store.py`（新增）、`tests/integration/test_snapshot_identity.py`
- `domain/contracts.py` 未修改；读取路径仅限任务指定的强制文件与沿调用链必需的相邻文件（snapshot_store/project_contract_store/lineage_registry/extraction_normalization/schema）。

## Work Performed（按 P1-1…P1-4、P2-5、P2-6 逐项）

**P1-1 锁定快照绑定证据注册表内容**：`EvidenceSnapshotManifest` 新增必填 `scientific_content_digest`（SHA-256，schema+模型同步）；`compute_scientific_content_digest` 公共实现（规范 JSON，片段按 fragment_id、事实按 fact_version_id 稳定排序，覆盖片段定位/原文/摘要与事实全部字段），写入（工厂）与验证（`_assert_evidence_context_bound` 重算比对）共用；缺少摘要的清单在重算路径失败关闭（不静默补算）。`_revalidate_inputs` 现在逐项重验片段/事实并重建注册表，返回重验证后的 `AEvidenceContext` 供全部后续使用。RED：禁用摘要比对 → 注册表+记录同步伪造（展示自洽、唯一防线是摘要）`DID NOT RAISE`。正向 `compute_locked_snapshot == _lock == store.read` 通过。

**P1-2 独立权威当前合同**：新增 `ProjectContractStore`（版本化、不可覆盖、`load_current` 取最高版本、`reload` 不漂移、路径越界拒绝）；`AEvidenceContext` 携带 `contract_store`；构建器经 `_assert_evidence_context_bound` 从权威存储重载当前合同并校验 project_id/contract_version/data_cutoff 与清单及上下文合同一致。RED：禁用权威加载 → 合同/清单/锁定/内容寻址存储/宇宙快照全部自洽改 999/2099 的伪造 `DID NOT RAISE`。正向当前合同通过；`reload`/重复读取不漂移。

**P1-3 疗效/安全完整绑定原子事实**：新增 `_assert_result_binding_matches_fact`，比较 normalized 数值、normalized_unit、denominator、numerator（≤分母）、population、timepoint/time_window、arm/cohort；事实缺少支撑字段失败关闭；dossier 提取循环在校验完全一致后才消费 binding。工厂为结果型事实填齐强类型字段（含 `NormalizationRecord`）。RED：禁用校验 → 分母 224 vs 999 疗效用例 `DID NOT RAISE`。

**P1-4 扩展 DTO 重新验证**：`_revalidate_records` 对每个 AV04–AV08 记录类型 `model_validate(model_dump)` 并只用返回对象；嵌套 `EvidenceField` 互斥校验与地域闭合随之生效。RED：禁用重验 → `region="美国"`（事实原文同为美国，唯一防线是地域闭合）`DID NOT RAISE`。

**P2-5 NFKC 等价日期**：`_normalized_date`（NFKC + `strptime("%Y-%m-%d")` 宽松解析 + ISO 规范输出）与 `_display_date`；版本化事件/历史状态日期比较与输出统一走规范日期；`_record_canonical` 日期部分改用规范日期。RED：禁用解析 → 非零填充 `2020-6-19` 用例被误拒（1 failed）。

**P2-6 中文原生显示**：`_user_facing_text` 拆分展示与比较：展示保留自然全角标点（仅去格式/零宽），安全比较走 NFKC 比较串；工程词变体拦截不削弱。RED：展示路径 NFKC → 全角 `，` 被改 ASCII（1 failed）。两个既有断言（企业条款、邻近观察）恢复为自然全角。

## Artifacts And Evidence

- `tests/unit/reports/a/test_revise_round4_closure.py`：38 个反例回归（P1-1×7 含正向、P1-2×3、P1-3×8、P1-4×12、P2-5×3、P2-6×2）全 GREEN。
- `tests/unit/test_project_contract_store.py`：5 个存储权威测试。
- 工厂升级：结果事实强字段、内容摘要、`ProjectContractStore` 持久化。

## Commands And Observations

```
uv run pytest tests/unit/reports/a -q                                 → 204 passed
uv run pytest tests/reports/a tests/unit/reports/a -q                 → 295 passed
uv run pytest tests/unit/test_gate_evaluator.py tests/reports/test_report_specific_gates.py \
  tests/reports/test_gate_override_strictness.py tests/integration/test_no_draft_when_blocked.py \
  tests/reports/a tests/unit/reports/a -q                             → 512 passed
uv run pytest tests/unit/test_project_contract_store.py tests/integration/test_snapshot_identity.py \
  tests/contract -q                                                   → 110 passed
uv run pytest tests -q --ignore=tests/browser --ignore=tests/acceptance → 1032 passed
uv run ruff check src/ci_workflow/reports/a src/ci_workflow/storage src/ci_workflow/capabilities \
  tests/unit/reports/a tests/unit/test_project_contract_store.py tests/integration/test_snapshot_identity.py \
  tests/reports/a                                                    → All checks passed!
uv run mypy --strict src                                             → Success: no issues found in 89 source files
```
RED 证据（故障注入逐项，均 1 failed 后恢复，`pages.py` 与最终版逐字节一致）：P1-1 摘要比对 / P1-2 权威加载 / P1-3 事实绑定 / P1-4 记录重验 / P2-5 日期解析 / P2-6 显示规范化，全部 `1 failed`。

## Blockers Or Missing Environment

无环境阻塞。残余问题（供 Codex 裁决）：
- 备份恢复流程曾短暂覆盖 strptime 与 `_record_canonical` 日期改动，已重新应用并以最终版复验全套；建议后续注入验证统一用单条 bash 执行（批量 subprocess 会吞输出）。
- P1-1 摘要覆盖"每条已验证片段与每条已接受事实"；若需把来源版本记录也纳入摘要范围（当前仅片段+事实），属最小扩展。
- 权威合同存储为新增最小只读实现；若工程已有项目数据库服务，可后续替换读取器而不改视图边界。

## Rerun Requests Or Next Step

- 未自行宣告验收、未提交。建议 Codex：复核 P1-1 摘要实现与 P1-2 权威存储后接受；可提交本轮修改并推进 Task 5.3。若需扩展摘要范围或替换合同存储读取器，请提供对应合同输入源。
