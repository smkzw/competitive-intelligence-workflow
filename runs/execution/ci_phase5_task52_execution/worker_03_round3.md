# Execution Output: ci_phase5_task52_execution - worker_03（第 3 轮 REVISE）

## Boundary And Context Check

- 直接修复当前工作树，未新建平行实现、未提交 Git、未做最终验收宣告。
- 修改文件（全部在允许范围）：
  - `src/ci_workflow/storage/snapshot_store.py`（本轮新增允许）：公共纯校验 `compute_locked_snapshot`
  - `src/ci_workflow/reports/a/pages.py`：P0–P2 全部机制
  - `src/ci_workflow/reports/a/contracts.py` / `__init__.py`：仅导出，无合同字段变化
  - `tests/unit/reports/a/**`：8 个既有测试夹具升级 + `test_revise_round3_closure.py`（56 个反例回归）
  - `tests/reports/a/*`：未改动（第 2 轮已含 event_id 回归）
- `domain/contracts.py` 未修改（`ProjectContract` 直接复用）；模板/HTML/PDF/PPT/浏览器/安全测试未触碰。

## Work Performed（按 P0/P1-A…P2 逐项）

**P0 关键证据阻断绝不生成**：8 个 `build_*_view` 在重算 `analyze_universe` 后调用 `_assert_report_ready`，`report_ready=False` 一律 `GateEvaluationError`；阻断说明留在分析/日志层。参数化测试覆盖 8 构建器 + 8 `assert_*_authoritative` 边界。RED：移除全部 8 个守卫 → `DID NOT RAISE`（1 failed）。

**P1-A 权威项目合同与内容寻址快照**：`AEvidenceContext` 新增 `project_contract: ProjectContract` + `store: SnapshotStore`；`_assert_evidence_context_bound` 增加：(a) 经 `snapshot_store.compute_locked_snapshot`（与 `SnapshotStore._lock` 同一规范 JSON 算法，`_lock` 已重构复用）重算并逐项比对 snapshot_id/sha256/relative_path/byte_size；(b) `store.read(locked)` 重新读取并重验清单（读路径自带摘要/字节/路径校验）；(c) project_id、contract_version、data_cutoff 与 manifest 完全一致。RED：禁用重算比对 → 篡改 sha256 用例以 `SnapshotIntegrityError` 失败；禁用合同绑定 → 篡改 project contract 版本 `DID NOT RAISE`。

**P1-B 所有公共输入重新验证**：共享 `_revalidate_inputs` 被全部 8 构建器调用并使用其返回对象：每个 `AProjectContract`/`ApplicableUniverseSnapshot`/`GateEvidenceBinding`/`RegistryResultsPostedEvidence` 重新 `model_validate`（拒绝 model_copy 改 eligibility、schema 9.9、model_construct 未报告带数值/零分母——后者由 `GateEvidenceBinding._binding_preserves_disclosure_contract` 重验捕获）；注册表逐项重验（每事实重新 model_validate + 原文==主片段原文 + 片段摘要重算）；全部绑定事实版本已注册（不再只限 dossier）。重验失败统一转 `GateEvaluationError`。RED：禁用重验 → eligibility 伪造用例失败（`UnboundLocalError`/`DID NOT RAISE` 形态）。

**P1-C 展示值必须由事实值支持**：`_assert_record_fact_bound` 增加 `canonical_value` 参数；`_record_canonical` 为每类记录定义唯一可审计规范证据值（AV04–AV08 全部 13 类）；比较经 NFKC 双侧规范化（事实原文为源文本、展示值经 `_user_facing_text` NFKC）。疗效/安全摘要增加「canonical binding value = 数值+单位 必须等于事实原文」校验。各记录集合按 `fact_version_id` 去重；不同监管 `event_id` 不得复用同一事实。夹具原文升级为规范串（非弱匹配）。RED：禁用比较 → 阶段/状态篡改用例 `DID NOT RAISE`。

**P1-D 完整档案是当前证据的完整投影**：`_assert_fact_coverage` 按封闭 field_id + 实体作用域（AV04 含 study_role 的 trial 作用域）要求「registry 事实集合 == 记录消费集合」，漏一条/多余一条均失败；dossier 经 5 个共享闭合获得跨 AV04–AV08 完整覆盖。RED：禁用覆盖 → 省略企业记录用例 `DID NOT RAISE`。

**P1-E 试验角色证据**：`study_role` 封闭字段（entity_id=trial_id 明确例外）绑定已接受角色事实；`_TRIAL_ROLE_FACT_TO_LAYER` 封闭映射（注册/关键→核心，特殊核心→特殊核心，支持性→支持性，其他适格→其他适格）；`EARLY_DECISION` 仅 `SPECIAL_CORE` 且必须有"特殊核心"事实；`OTHER_ELIGIBLE` 必须 raw=="其他适格"；无证据默认排除。RED：移除事实 → 用例 `AttributeError` 失败。

**P2 中文用户文本规范化**：`_user_facing_text` 先 NFKC + 移除格式/零宽字符（Cf 类别 + ZWSP 集合），原文直接查下划线；按空白分词后 (a) 去分隔符合并小写查工程词（back-end→backend、model-copy→modelcopy），(b) camel-case 拆分逐段查（BackendState→backend）。`Gate`/`BackendState`/`back-end`/零宽/全角/`model-copy` 拒绝；`Dupixent`/`IL-4Rα`/`NCT02407756`/`Novartis`/`aggregate` 通过（正反例同测）。RED：禁用两处词表检查 → `Gate` 用例 `DID NOT RAISE ValidationError`。

## Artifacts And Evidence

- `tests/unit/reports/a/test_revise_round3_closure.py`：56 个反例回归（P0 参数化 16 + P1-A 5 + P1-B 5 + P1-C 8 + P1-D 4 + P1-E 3 + P2 15）全 GREEN。
- `src/ci_workflow/storage/snapshot_store.py`：`compute_locked_snapshot` 公共纯函数（`_lock` 复用，单一算法）。
- 8 个视图测试文件夹具升级：规范 raw 值、study_role 事实（独立 locator）、p-terminated 分层 SPECIAL_CORE、P0 阻断用例改为期望 raise、NFKC 展示断言（全角逗号→ASCII）、显式缺失状态用例改绑自身事实。

## Commands And Observations

```
uv run pytest tests/unit/reports/a -q                                 → 166 passed
uv run pytest tests/reports/a tests/unit/reports/a -q                 → 257 passed
uv run pytest tests/unit/test_gate_evaluator.py tests/reports/test_report_specific_gates.py \
  tests/reports/test_gate_override_strictness.py tests/integration/test_no_draft_when_blocked.py \
  tests/reports/a tests/unit/reports/a -q                             → 474 passed
uv run pytest tests/contract/test_project_contract.py tests/integration/test_snapshot_identity.py \
  tests/contract -q                                                   → 105 passed
uv run pytest tests -q --ignore=tests/browser --ignore=tests/acceptance → 989 passed
uv run ruff check src/ci_workflow/reports/a src/ci_workflow/storage/snapshot_store.py \
  tests/unit/reports/a tests/reports/a                                → All checks passed!
uv run mypy --strict src                                              → Success: no issues found in 88 source files
```
故障注入 RED 证据逐项见上（P0/P1-A×2/P1-B/P1-C/P1-D/P1-E/P2 均 1 failed），注入后恢复，`pages.py` 与备份逐字节一致，全套复绿。

## Blockers Or Missing Environment

无环境阻塞。未闭合项（供 Codex 裁决）：
- P1-A 的 manifest `contract_version`/`data_cutoff` 篡改同时被内容寻址重算拦截（防御纵深）；合同绑定检查的独立 RED 通过篡改 `ProjectContract` 本体验证。
- 记录展示值与事实原文的比较采用「NFKC 规范化串相等」；若要求逐字段（如单位拆分、日期语义化）比对需引入字段级映射合同（超出本轮范围）。
- `study_role` 事实的原始词表（注册/关键、特殊核心、支持性、其他适格）为封闭枚举，后续若需新增层需同步扩展映射与 5.1 角色合同。

## Rerun Requests Or Next Step

- 未自行宣告验收、未提交。建议 Codex：复核 P0 阻断语义（含 `tests/reports/a` 阻断文档层保持）与 P1-A 内容寻址公共函数后接受；后续可提交本轮修改并推进 Task 5.3。若需关闭逐字段展示值比对或扩展试验分层词表，请提供字段级事实合同。
