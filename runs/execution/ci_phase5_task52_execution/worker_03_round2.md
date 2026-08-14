# Execution Output: ci_phase5_task52_execution - worker_03 (REVISE 修复轮)

## Boundary And Context Check

- 修复在既有 5.2 实现上直接进行，未新建平行实现，未提交 Git。
- 修改文件全部落在允许范围：
  - `src/ci_workflow/reports/a/pages.py`（本会话内唯一重写的生产文件）
  - `src/ci_workflow/reports/a/contracts.py`（`RegulatoryEventRecord` 增加稳定 `event_id`）
  - `src/ci_workflow/reports/a/__init__.py`（导出新增符号）
  - `tests/reports/a/{test_maturity_gate,test_no_top_n,test_result_bearing_gate}.py`（仅事件合同变化的精确回归：`event_id` 填充）
  - `tests/unit/reports/a/**`（7 个既有测试文件升级 + `_evidence_factory.py` 共享夹具 + `test_revise_closure.py` 反例回归）
- `analysis.py` 未修改（仅读取合同事件字段，事件 ID 无影响）；未触碰模板/HTML/PDF/PPT/浏览器/安全测试。

## Work Performed

### 关闭机制（按反例）

1. **CE1 证据快照闭合**：新增 `AEvidenceContext`（`LockedSnapshot` + `EvidenceSnapshotManifest` + `ScientificLineageRegistry` 真实合同捆绑）。`_assert_evidence_context_bound` 校验 kind=evidence、锁定 ID == `snapshot.evidence_snapshot_id`、manifest 项目一致、manifest 的 fact/fragment/source-version ID 与注册表精确一致；`_assert_record_fact_bound` 逐记录校验事实已接受、entity 绑定本产品、字段属于记录类型封闭集合（每类记录独立字段集合）、来源定位与主片段定位经 `_render_locator` 精确一致。所有构建器必传 `evidence`；同一业务记录换 `evidence_snapshot_id` 失败关闭；伪 fact/伪 locator 拒绝。`contract_version`/`data_cutoff` 因 `ApplicableUniverseSnapshot`/`AProjectContract` 均不携带而无法在本层交叉校验（见不确定性）。
2. **CE2 分析权威**：全部 8 个构建器删除 `analysis` 参数，改为 `(projects, snapshot, evidence, bindings, *, …records, results_posted_evidence=())`，内部从当前输入重跑 `analyze_universe`；`_assert_view_inputs_bound` 仍做合同↔快照↔分析对齐。签名测试断言无 `analysis` 参数。
3. **CE3 完整档案**：`ProductDossier` 新增临床组合行、中国/境外监管分轨（稳定 `event_id`）、企业角色/合作/权益/交易/条款、专利族/法域成员/范围/期限/独占、历史状态与邻近观察；疗效/安全用第 5.1 步强类型绑定推导的 `DossierEfficacyRecord`/`DossierSafetyRecord`（定义/方向/单位/时间点/人群/治疗组/对照/分母/报告值/披露标签），绑定缺字段即 `GateEvaluationError`（不用空解释文本）；`result_bearing` 档案必须携带非空疗效+安全记录。`build_product_dossier_view` 复用全部专项闭合校验。
4. **CE4 试验分层**：`ClinicalTrialLayer` 封闭枚举（注册/关键、特殊核心、支持性、其他适格）+ 合同角色→允许分层封闭映射；非核心试验（无合同核心角色证据）默认排除；分层与合同角色越权失败关闭。记录 `role` 字段替换为 `layer`。
5. **CE5 稳定事件 ID**：`RegulatoryEventRecord`（contracts.py）与 `RegulatoryEventVersionRecord` 增加必填 `event_id`；版本化事件按 `event_id` 多重集精确绑定，且记录的类型/地域/日期必须与合同事件一致；废除「类型+地域+日期」计数配对。5.1 全部回归保持通过（`tests/reports/a` 91 通过）。
6. **CE6 历史状态闭合**：`HistoricalStatusRecord` 必填 `regulatory_event_id`；闭合要求事件存在于合同、状态类型↔事件类型封闭映射（暂停→PAUSE 等）、活跃临床开发（`DevelopmentMaturity.CLINICAL`）产品禁止终止/撤回/放弃状态、事实绑定当前证据快照；相邻观察与正式监管状态保持独立类型。
7. **CE7 用户文本权威**：`_user_facing_text` 拒绝下划线后台枚举（直接检查原文）与封闭词表（prompt/log/backend/enum/snapshot/binding/fact_version/…），医学合理英文（IL-4Rα、Dupixent、NCT 号等）放行；应用于全部用户可见标签/描述/事实字段（行+记录）。
8. **CE8 视图作用域与渲染边界**：8 个视图模型增加 `content_digest`（规范 JSON SHA-256，`model_validator` 重算比对，`model_construct` 无法伪造）；`ProductOverviewView` 增加 `ViewScope`（COMPLETE 必须等于锁定快照，FILTERED 为派生子视图）；`assert_*_view_authoritative` 8 个可调用权威函数按当前输入重建并精确比对，拒绝旧视图与手工 DTO。

### RED 证据（故障注入逐类验证）

| 反例 | 注入故障 | 结果 |
|---|---|---|
| CE1 | 移除 `_assert_evidence_context_bound` 调用 | `1 failed` |
| CE4 | 关闭非核心试验排除分支 | `1 failed` |
| CE5 | 关闭 `event_id` 存在性检查 | `1 failed` |
| CE6 | 移除历史状态闭合调用（history 构建器） | `1 failed` |
| CE7 | `_user_facing_text` 退回 `_text` | `1 failed` |
| CE8 | 权威校验 `rebuilt != view` 置恒假 | `1 failed` |

CE2/CE3 为结构性反例：旧代码构建器带 `analysis` 参数、档案无新字段，对应测试在旧代码下必然失败（签名断言/字段访问即 RED）；注入后恢复，`test_revise_closure.py` 全 20 项 GREEN。

## Artifacts And Evidence

- `tests/unit/reports/a/test_revise_closure.py`：20 个反例回归测试（本快照接受/换快照拒绝/伪 fact/locator 拒绝全覆盖）。
- `tests/unit/reports/a/_evidence_factory.py`：共享证据夹具工厂（真实 `EvidenceRepository` + `ScientificLineageRegistry` + `SnapshotStore` 内容寻址锁定，每次调用独立存储子目录）。
- 7 个既有测试文件升级：`_snapshot` 接受真实 `evidence_snapshot_id`、构建器新签名、`event_id`/`layer`/`regulatory_event_id`、确定性测试改为同一锁定输入两次构建。

## Commands And Observations

```
uv run pytest tests/unit/reports/a -q                                  → 110 passed
uv run pytest tests/reports/a tests/unit/reports/a -q                  → 201 passed
uv run pytest tests/unit/test_gate_evaluator.py tests/reports/test_report_specific_gates.py \
  tests/reports/test_gate_override_strictness.py tests/integration/test_no_draft_when_blocked.py \
  tests/reports/a tests/unit/reports/a -q                              → 418 passed
uv run pytest tests -q --ignore=tests/browser --ignore=tests/acceptance → 933 passed
uv run ruff check src/ci_workflow/reports/a tests/unit/reports/a tests/reports/a → All checks passed!
uv run mypy --strict src                                               → Success: no issues found in 88 source files
```
- 测试中发现的缺陷已就地修复：工厂循环变量泄漏（`entity_id` 取到最后一项）、重复片段冲突（同 locator+同文本）、`_user_facing_text` 下划线被分词器吞掉（改为原文直查）、`ruff format` 误剥 `Literal` 引号（改用 `ViewScope` 枚举）。

## Blockers Or Missing Environment

无环境阻塞。残留不确定性（供 Codex 裁决）：
- `EvidenceSnapshotManifest.contract_version`/`data_cutoff` 无法与 A 层输入交叉校验——`ApplicableUniverseSnapshot` 与 `AProjectContract` 均不携带这两个字段；本层已校验项目一致与 fact/fragment/source 清单精确一致。若需关闭该项，需把项目合同版本/数据截止日传入视图层（超出本任务文件范围）。
- 记录展示值（如到期日）与注册表事实 `raw_value` 未做值级比对（CE1 约束为实体/字段/来源片段/定位吻合）；如需值级一致性校验需扩展记录↔事实映射合同。

## Rerun Requests Or Next Step

- 未自行声明验收、未提交 Git。建议 Codex：复核 CE1 证据上下文与 CE8 权威函数后接受；随后可提交本轮修改（`feat: harden report A view authority and evidence closure`）并推进 Task 5.3。若需关闭 contract_version/data_cutoff 交叉校验，请提供项目合同版本输入源。
