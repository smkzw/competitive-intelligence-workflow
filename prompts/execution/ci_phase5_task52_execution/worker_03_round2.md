# 第 5.2 步同会话修复任务

你是第 5.2 步原实现会话的修复执行者。独立验证者已经给出 REVISE。请在当前工作区直接修复，不新建平行实现，不提交 Git。目标不是让现有测试继续绿，而是先把下列反例写成会失败的精确回归测试，再做最小但完整的架构修复。

## 本轮必须关闭的反例

1. AV04—AV08 的 `fact_version_id`、`locator` 或展示事实若不属于当前 `ApplicableUniverseSnapshot.evidence_snapshot_id` 对应的不可变证据快照，必须失败关闭。把同一业务记录搬到另一个 `evidence_snapshot_id` 后不得继续被接受。
2. 所有视图构建器不得信任调用方传入或通过 `model_copy` 伪造的 `UniverseAnalysisResult`。必须从当前 `projects + snapshot + GateEvidenceBinding` 重新执行既有 `analyze_universe`，并对外部分析结果做逐字段一致性验证或彻底取消该不可信输入。
3. AV03 产品档案必须形成真正的完整档案：已有身份/成熟度基础上，纳入该产品的临床项目组合、国内/全球监管轨道、企业角色/合作/交易/权益、专利/监管保护、历史暂停/终止/撤回/放弃状态，并保留稳定详情路由。疗效/安全性可使用第 5.1 步已有的强类型摘要作为本阶段过渡，不能用空的解释文本假装完成；不得复制 B 报告。
4. AV04 非核心试验不能仅凭自由记录进入临床组合。必须绑定既有试验角色/纳排规则的已接受科学证据；核心、特殊核心、支持层及其他适格层的语义要明确，默认排除项不得进入。
5. AV05 监管事件必须有稳定不可变的 `event_id`，版本记录按该 ID 精确绑定，不能用“事件类型+司法辖区+日期”的计数配对。必要时可同步修改 `contracts.py`、`analysis.py` 与第 5.1 步测试，但必须保持第 5.1 步全部回归通过。
6. AV08 历史状态必须与当前产品成熟度和真实监管事件闭合：撤回/终止/暂停/放弃必须引用相应 `regulatory_event_id` 及当前证据事实；不得给仍处于活跃临床开发、且没有对应监管事件的产品伪造撤回记录。相邻观察与正式监管状态必须分开。
7. 所有用户可见标签、说明和事实文本需要中文临床环境原生表达。允许药物名、靶点、机构名、NCT 号等医学上合理的英文/缩写，但必须拒绝 `prompt`、`log`、`backend_enum`、带下划线的后台枚举、快照/绑定/内部状态等程序员或日志语言直接进入用户视图。不要用“所有英文一律拒绝”的粗暴规则。
8. 直接构造、`model_construct`、`model_copy` 得到的空/残缺 `ProductOverviewView`、空 `ClinicalPortfolioView`、伪造 `AProjectContract` 锚点都不能成为权威输出。完整视图与筛选子视图必须有明确不同的作用域；渲染边界必须有可调用的权威校验函数，重新验证当前项目、快照、证据清单与内容摘要，拒绝旧视图和手工 DTO。

## 证据版本实现约束

- 复用现有 `LockedSnapshot`、`EvidenceSnapshotManifest`、`ScientificLineageRegistry`、`AtomicFactVersion`、`VerifiedEvidenceFragment` 和 `SnapshotStore` 合同，不要另造一个由页面记录自行声明、可伪造的 `evidence_snapshot_id` 字段来冒充验真。
- 证据上下文至少验证：锁定快照 kind 为 evidence；锁定 ID 与适用宇宙快照一致；manifest 项目/合同/截止日一致；manifest 中 fact/fragment ID 与传入注册表精确一致或为其经明确规则允许的闭合集合；所有引用事实已接受、实体/字段/来源片段/locator 与当前业务记录吻合。
- 页面记录引用何种 `field_id`、`entity_id`、事件/试验/产品身份，要用封闭映射或强类型合同校验，不接受任意事实版本 ID 能支持任意字段。
- 如果现有测试夹具没有真实证据快照/注册表，请升级共享 fixture factory；不要在每个测试里散落无法审计的伪摘要。

## 允许修改范围

- `src/ci_workflow/reports/a/pages.py`
- `src/ci_workflow/reports/a/contracts.py`
- `src/ci_workflow/reports/a/analysis.py`
- `src/ci_workflow/reports/a/__init__.py`
- `tests/unit/reports/a/**`
- `tests/reports/a/**`（仅修复合同变化引起的精确回归）

若必须触及其他生产文件，先在最终交接中明确原因；不要扩展到模板、HTML、PDF/PPT、浏览器或安全测试。

## 实施与验证顺序

1. 逐个复现上述 8 类反例，并先看到 RED；每类至少一个精确测试，证据串联类要覆盖“本快照接受、换快照拒绝、伪 fact/locator 拒绝”。
2. 实现最小完整修复，避免用字符串黑名单或多处重复逻辑糊住测试。
3. 运行：
   - `uv run pytest tests/unit/reports/a -q`
   - `uv run pytest tests/reports/a tests/unit/reports/a -q`
   - `uv run pytest tests/unit/test_gate_evaluator.py tests/reports/test_report_specific_gates.py tests/reports/test_gate_override_strictness.py tests/integration/test_no_draft_when_blocked.py tests/reports/a tests/unit/reports/a -q`
   - `uv run ruff check src/ci_workflow/reports/a tests/unit/reports/a tests/reports/a`
   - `uv run mypy --strict src`
4. 不运行全量浏览器测试，本轮只做第 5.2 步数据模型与权威边界。

## 交接要求

返回紧凑执行报告：修改文件、每个反例的关闭机制、RED 证据、最终测试/静态检查精确结果、任何尚未关闭的不确定性。不得自行声明任务验收，不得提交 Git。
