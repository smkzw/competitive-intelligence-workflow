# Execution Output: ci-phase9-task93-optional-monitoring - worker_01

## Boundary And Context Check

- 在授权工作目录内工作;初始读集(`context/ci-phase9-task93-optional-monitoring_execution_context.md`、`plans/codex_execution_ci-phase9-task93-optional-monitoring.md`)之外,为理解已批准 Task 9.3 合同与既有先例,额外读取:`.trellis/tasks/09-01-phase-9-task-93-optional-monitoring/`(prd/design/implement/task.json/research)、`.trellis/spec/backend/quality-guidelines.md`、`docs/specs/competitive-intelligence-workflow-design-v1.2.md` §17.3/§7、correction-proposal 先例(schema + `application/correction_service.py` + 其合同测试)、`cli.py` 包完整性校验、`tests/contract/test_package_manifest.py`、`scientific_qc` 双布局解析器、`domain/ids.py`、`storage/event_store.py`、`skills/_internal/monitoring/SKILL.md`。均为只读。
- 写入仅限本工作项授权产物(见 Artifacts)。未触碰生产路径、未安装包、未修改他人文件。
- 未做视觉/PPT/PDF/临床/监管终审;未创建 runner 报告文件。

## Work Performed

实现工作项 1「变更候选 JSON Schema、Python 合同、稳定去重摘要和 package-manifest 双布局登记」:

1. **Python 合同模块 `src/ci_workflow/domain/monitoring.py`**(新增,~740 行):
   - 机器合同模型:`MonitoringSourceIdentity`(来源稳定 ID/版本/可复现定位/原始链接,稳定 ID 模式校验)、`MonitoringDiscoveryRecord`(仅 `change_found`;无变化/未公开/技术失败由事件流承载,不进候选)、`MonitoringDiagnosticRecord`(失败类别 7 值、尝试轮次、已尝试方法、下一步、用户指引;`needs_user_assistance` 必须携带已尝试方法;新增 `recovered` 恢复记录使候选能回到健康态而历史失败记录保留)、`MonitoringUserDispositionRecord`(只有 start_normal_refresh/deferred 两种决定)、`MonitoringRefreshHandoff`(内容寻址交接单:候选 ID/摘要、项目 ID、项目合同版本 int≥1、来源身份、建议复核范围;`created_at` 不参与寻址以保证处置重放幂等同标识)、`MonitoringChangeCandidate`(§17.3 全部最低字段;`extra=forbid`、frozen)。
   - **稳定去重摘要** `monitoring_dedupe_digest`:项目、来源稳定 ID/版本/定位、实体、声明域、变化类型、当前值、候选值的规范 JSON SHA-256;原始链接/发现时间/追加历史不参与(同一业务变化重复发现同一身份;不同定位/版本/候选值分裂为不同候选)。候选 ID 由摘要经 `stable_id("monitoring-candidate", digest)` 派生,调用方不能自带。
   - **失败关闭双层防线**(quality-guidelines):构造边界 `model_validator` 重算摘要比对 `dedupe_digest`/`candidate_id`;公开聚合边界 `verify_candidate_dedupe_identity` / `verify_refresh_handoff_addressing` 从当前序列化内容重推导,`model_copy(update=...)` 漂移在聚合前失败关闭。规范构造入口 `build_change_candidate` / `build_refresh_handoff` 拒绝自带标识。
   - 冻结追加事件词表常量(供 worker_02 使用):`monitoring.candidate.discovered / .rediscovered / .diagnostic_updated / .disposition_recorded`、`monitoring.refresh_handoff.created`。
   - 中文转译:`outcome_guidance_zh`(五类观察结果,PRD 验收 4 的四类阻断区分:无变化/未公开/技术失败/需协助)、`change_type_zh`、`disposition_zh`、`acquisition_status_zh`、`diagnostic_status_zh`、`failure_category_zh`;输出不含内部工程化标签。
2. **JSON Schema `schemas/monitoring-change-candidate.schema.json`**(新增)及**包内逐字一致副本** `src/ci_workflow/schemas/monitoring-change-candidate.schema.json`(双布局,Draft 2020-12;沿用 correction-proposal 的 HexDigest/StableId/DateTime/ProseZh/InternalLabelGuard/VisibleValue 约定;条件规则:交接单↔启动刷新决定互锁、处置记录支撑、需协助须已尝试方法、诊断状态与记录支撑)。
3. **`package-manifest.json`** `components.schemas` 登记 `schemas/monitoring-change-candidate.schema.json`(满足 test_package_manifest 的「声明集合 == 实际文件集合」闭合校验)。
4. **聚焦测试 `tests/contract/test_monitoring_change_candidate_contract.py`**(新增,21 用例):Schema 合法性、双布局逐字一致、清单登记、构造→Schema roundtrip、全生命周期(重复发现合并/诊断/恢复/处置/交接)逐阶段过 Schema、摘要区分性与同一性(7 维变化各自分裂、URL/发现时间/备注不分裂)、`model_copy` 对抗测试(候选值/摘要/ID/交接范围漂移均被聚合边界拒绝)、交接单内容寻址幂等(同绑定不同 created_at 同 ID;范围变化不同 ID)、待处理不得携带交接单、处置成员匹配 fail-closed、四类中文提示可区分且无内部标签、事件词表冻结、合同封闭性(无 fact/claim/snapshot/report 写入面)。

## Artifacts And Evidence

| 文件 | 状态 | 说明 |
|---|---|---|
| `src/ci_workflow/domain/monitoring.py` | 新增 | Python 合同 + 去重摘要 + 标识派生 + 中文转译 |
| `schemas/monitoring-change-candidate.schema.json` | 新增 | §17.3 机器合同(Draft 2020-12) |
| `src/ci_workflow/schemas/monitoring-change-candidate.schema.json` | 新增 | 包内副本,与根目录逐字节一致(diff 验证) |
| `package-manifest.json` | 修改(1 行) | components.schemas 增加登记 |
| `tests/contract/test_monitoring_change_candidate_contract.py` | 新增 | 21 项聚焦合同测试 |

依赖方向:本模块仅导入 `ci_workflow.domain.ids`;`src/` 内无任何核心服务导入本模块(grep 验证,可卸载性成立)。

## Commands And Observations

- `uv run pytest tests/contract/test_monitoring_change_candidate_contract.py` → **21 passed**。
- `uv run pytest tests/contract/ tests/unit/` → **765 passed, 1 failed**;唯一失败 `tests/contract/test_offline_assets.py::test_html_ppt_runtime_has_required_navigation_presenter_and_offline_boundaries`。经 `git stash` 往返验证:干净树上该测试通过,恢复工作树后复现——失败源于工作树上**既有的未提交资产改动**(`assets/html-ppt/runtime.*` 等,会话开始前已存在的 M 状态),与本次变更无关,未处理(超出授权范围)。
- `uv run python -m ci_workflow package verify --root .` → `PACKAGE_OK version=0.1.0a0 stage=phase-2-accepted`(含 Schema 清单闭合校验)。
- `uv run mypy src/ci_workflow/domain/monitoring.py` → no issues(strict)。
- `uv run ruff check <两个新文件>` → All checks passed(仓库未强制 ruff format,既有文件同样不满足 format,保持一致)。
- `tests/contract/test_package_manifest.py`、`test_dependency_manifest.py`、`test_correction_proposal_contract.py`、`test_scientific_qc_verdict_contract.py` → 26 passed。

## Blockers Or Missing Environment

1. **(集成裁决,需 Codex 决定)与 worker_02 的合同重复与词表分歧**:并行会话中 `src/ci_workflow/application/monitoring_service.py`(worker_02 产物,非本人修改)内含一套**平行合同**:自己的 `MonitoringSourceIdentity`/`DiscoveryRecord`/`DiagnosticRecord`/`UserDispositionRecord`/`MonitoringRefreshHandoff`/`ChangeCandidate` 模型与自己的去重摘要实现,且枚举词表与本工作项登记的 Schema 不一致:
   - 观察结果:对方 `completed_with_change/completed_no_change/...` vs 本合同 `change_found/no_change/confirmed_not_public/...`;
   - 获取状态:对方 `acquired/recoverable_failure/user_assistance_required` vs 本合同 `acquired/acquired_with_user_assistance`;
   - 诊断状态:对方 `not_required/auto_recovery_pending/user_assistance_required` vs 本合同 `healthy/technical_failure_recoverable/needs_user_assistance`;
   - 用户处置:对方 `pending/refresh_requested/deferred` vs 本合同 `pending/start_normal_refresh/deferred`;
   - 事件词表:对方 `monitoring.observation.recorded` 族 vs 本合同冻结的 `monitoring.candidate.*` 族。
   对方文件不引用 `schemas/monitoring-change-candidate.schema.json` 也不导入 `domain/monitoring.py`,其 JSON 投影大概率不通过已登记 Schema(`monitoring/inbox/` 使用 §17.3 Schema 是 §7 合同要求)。工作项 1 被定义为合同层、工作项 2 为服务层,原意应是分层复用;建议以登记进包清单的 Schema + `domain/monitoring.py` 为准,令 service 迁移到共享合同(或由 Codex 明确裁决以 service 内词表为准并回改 Schema/清单)。我未修改对方文件。
2. (非阻塞,记录)工作树存在多项他人未提交改动(html-ppt/portal 资产、`schemas/package-manifest.schema.json` 的 internal_skills 15→16 与 cli 目录 6→7 等),后者为会话前既有状态,非本人所为。
3. 环境完备(uv/pytest/mypy/ruff/jsonschema 均可用),无缺失。

## Rerun Requests Or Next Step

1. **请 Codex 裁决合同权威版本**(Blocker 1):确定唯一词表后,保留方为唯一真源;若以本合同为准,worker_02 的 service 需改为导入 `ci_workflow.domain.monitoring` 并复用其事件常量与 `verify_*` 聚合边界检查(这同时满足其「所有公开聚合边界重新计算摘要」的实现声明)。
2. 需 Codex 复核的本合同设计裁决(均已在代码注释/Schema description 中言明):候选 `contract_version` 为监测能力合同版本 "1.0"(区别于交接单绑定的项目合同版本 int);交接单 `created_at` 不参与内容寻址以幂等重放;诊断记录含 `recovered` 恢复态;`source_url` 不参与去重摘要;恢复轮次阈值留给服务层配置(合同只冻结「需协助必须提供已尝试方法」)。
3. 遗留验证(属后续工作项,非本人范围):worker_03 的可卸载性/图节点回归、`monitoring/inbox/` 投影由事件流恢复、只读交接单进入 Task 9.2 的端到端联测;以及与本合同对齐后的全量回归。
4. 复现命令:`uv run pytest tests/contract/test_monitoring_change_candidate_contract.py -q`;`uv run python -m ci_workflow package verify --root .`。
