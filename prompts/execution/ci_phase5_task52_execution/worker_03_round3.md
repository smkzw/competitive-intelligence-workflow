# 第 5.2 步同会话修复第 3 轮

继续原 worker_03 会话。Luna 第 2 轮独立复核仍为 REVISE，完整报告在：
`runs/conference/ci_phase5_task52_verify/luna_verifier_round2.md`。

请直接修复当前工作树，不提交 Git。先把复核报告中的每个可运行反例原样转成回归测试，看到 RED 后再实现。不得只扩大字符串黑名单或给测试数据打补丁。

## P0：关键证据阻断时绝不生成

- 所有 8 个公共 `build_*_view` 入口必须在重算 `analyze_universe` 后检查 `analysis.report_ready`。
- 任一产品关键证据不足时，所有权威门户视图都抛出 `GateEvaluationError`，不得生成含“尚未公开”的草稿视图；阻断说明留在分析/日志文档层，不进入门户。
- 加参数化测试覆盖 8 个构建器和对应 `assert_*_authoritative` 边界。

## P1-A：权威项目合同和内容寻址快照

- `AEvidenceContext` 必须携带当前 `ci_workflow.domain.contracts.ProjectContract`（不是 AProductContract），并在每次公共构建入口重新校验：project_id、contract_version、data_cutoff 与 `EvidenceSnapshotManifest` 完全一致。
- 对 `LockedSnapshot + EvidenceSnapshotManifest` 重新计算规范 JSON（与 `SnapshotStore` 完全同一算法）、sha256、byte_size、snapshot_id、relative_path，并逐项比对；篡改任一项失败关闭。优先在 `storage/snapshot_store.py` 增加可复用的公开纯校验函数，不要在 pages.py 复制一套将来会漂移的算法。
- 测试工厂用真实 `ProjectContract`，覆盖锁定元数据、manifest 合同版本/截止时间篡改。

## P1-B：所有公共输入重新验证

- 建立一个所有 8 个构建器共享的输入准备函数，并真正使用其返回的重新验证对象：
  - `AProjectContract.model_validate(model_dump(...))`
  - `ApplicableUniverseSnapshot.model_validate(...)`
  - 每条 `GateEvidenceBinding.model_validate(...)`
  - `RegistryResultsPostedEvidence` 同理
  - `AtomicFactVersion`、已验证片段及注册表内部一致性逐项重新校验；不得信任 `ScientificLineageRegistry.model_copy/model_construct`。
- 所有视图都要求传入 bindings 的事实版本已在当前 registry 接受，不再只在 dossier 检查。
- 原反例必须拒绝：eligibility 被 model_copy 改 excluded；snapshot schema 9.9；未登记 binding；NOT_REPORTED 却带数值/零分母的 model_construct binding；registry raw_value 被 model_copy/model_construct 改写。

## P1-C：展示值必须由事实值支持

- 扩展 `_assert_record_fact_bound`：除 ID/实体/字段/定位外，必须校验该记录的用户展示内容与 `AtomicFactVersion.raw_value/normalized_value` 一致。优先从事实派生视图值；若采用规范串比对，为每类记录定义一个唯一、可审计的 canonical evidence value，并升级夹具原文，不能用“包含任一词”这类弱匹配。
- 覆盖 AV04–AV08 全部记录类型：临床地域/阶段/状态；监管事件；组织角色/企业名；关系/交易/权益/公开条款；专利族/成员法域状态/范围/期限/独占；历史状态/日期/相邻观察。
- 疗效与安全摘要的数值、单位、分母、试验、时间点、人群、治疗/对照、定义必须与当前已接受事实/绑定闭合。至少让当前事实原文与 canonical binding value 精确一致；保留同一 fact ID 但改为 `999.9 伪造单位` 或 `0.1 伪造安全单位` 必须拒绝。
- 同一事实版本不得支持两个相互独立或冲突的页面记录；各记录集合按 fact_version_id 去重。不同监管 event_id 不得复用同一事实版本。

## P1-D：完整档案是当前证据的完整投影

- 对当前 registry 中属于 AV04–AV08 封闭 field_id、且 entity 属于快照产品的事实，必须全部由相应记录消费；漏一条、重复一条、被错误类型消费均失败关闭。
- 没有这类已接受事实时，相应扩展模块可为空并呈现明确缺失状态（后续视图层实现）；但“registry 已有事实而调用方省略 records”绝不能得到貌似完整档案。
- `build_product_dossier_view` 必须执行跨 AV04–AV08 的完整覆盖检查。正向夹具有全部事实时，空传企业/专利/历史要失败。

## P1-E：试验角色证据

- 不得再把 `CoreTrialRole.EARLY_DECISION` 无条件映射为 `OTHER_ELIGIBLE`。
- 为临床组合记录增加已接受、当前快照内的试验角色/纳排事实绑定（field_id 使用封闭的 study-role 字段）；角色事实要绑定 trial_id，而不是只绑定产品。若现有 `AtomicFactVersion.entity_id` 只能单实体，角色事实 entity_id 应为 trial_id，记录校验允许该明确例外。
- 注册/关键、特殊核心、支持层、其他适格分别有明确证据语义：EARLY_DECISION 只有在独立事实明确支持“特殊核心”时进入 SPECIAL_CORE；OTHER_ELIGIBLE 必须有单独适格规则事实，不能从 EARLY_DECISION 自动推出。无证据默认排除。
- 若需要同步调整 `CoreTrialRecord` 合同和第 5.1 测试，做最小向前兼容变化并保持全部 5.1 回归通过。

## P2：中文用户文本规范化

- 对用户可见文本先做 Unicode NFKC，移除零宽/格式控制字符，做大小写与 camel-case/连字符/标点拆分的工程词识别。
- `Gate`、`BackendState`、`back-end`、`back​end`、全角 backend、`model-copy` 必须拒绝；`Dupixent`、`IL-4Rα`、`NCT02407756`、`Novartis` 必须通过。
- 不要用任意子串拒绝导致 `aggregate` 等正常词误伤；测试必须同时有正反例。

## 允许范围

上一轮范围，外加为统一权威校验所必需的：
- `src/ci_workflow/storage/snapshot_store.py`
- `src/ci_workflow/domain/contracts.py`（仅若确有必要，优先不改）
- 对应 `tests/unit/test_snapshot_store.py` 或现有快照测试

不得进入模板/HTML/PDF/PPT/浏览器/安全测试。

## 验证

依次运行并报告精确结果：

1. 新增的第 2 轮反例测试。
2. `uv run pytest tests/unit/reports/a -q`
3. `uv run pytest tests/reports/a tests/unit/reports/a -q`
4. `uv run pytest tests/unit/test_gate_evaluator.py tests/reports/test_report_specific_gates.py tests/reports/test_gate_override_strictness.py tests/integration/test_no_draft_when_blocked.py tests/reports/a tests/unit/reports/a -q`
5. 涉及的 snapshot/domain tests。
6. `uv run ruff check ...` 目标文件。
7. `uv run mypy --strict src`

不要自行宣告验收，不提交。交接要按上述 P0/P1-A 至 P2 逐项说明机制和 RED/GREEN 证据，明确任何未闭合项。
