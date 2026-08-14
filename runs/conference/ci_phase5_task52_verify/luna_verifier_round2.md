Verdict: REVISE

P0

1. 关键证据缺失仍可生成并通过权威渲染

- 文件/符号：`pages.py:build_product_overview_view`、`assert_product_overview_view_authoritative`；`analysis.py:analyze_universe`
- 最小构造：将产品 `target_mechanism` 改为 `EvidenceField(state=NOT_YET_DISCLOSED)`。
- 实际结果：`analysis.report_ready=False`、产品被阻断，但总览仍返回 5 个产品；渲染权威校验也通过，页面显示“尚未公开”。
- 预期结果：`GateEvaluationError`，不得进入可渲染权威视图。
- 未捕获原因：测试只覆盖空/子集 DTO，不覆盖 `report_ready=False` 的真实分析链；`pages.py` 未检查 `analysis.report_ready`。

P1

2. 锁定快照未做内容寻址复核，合同版本/截止时间也未绑定

- 文件/符号：`pages.py:_assert_evidence_context_bound`
- 最小构造：
  - `locked.model_copy(update={"sha256": "0"*64, "relative_path": "forged.json", "byte_size": 1})`
  - `manifest.model_copy(update={"contract_version": 999, "data_cutoff": datetime(2099, 1, 1, tzinfo=UTC)})`
- 实际结果：产品总览/竞争格局均接受。
- 预期结果：重新读取并核对 `sha256`、`relative_path`、`byte_size`、manifest 内容后拒绝。
- 未捕获原因：现有测试只验证 `snapshot_id` 和 ID 集合，没有篡改锁定元数据或合同版本。
- `AProjectContract` 没有 `contract_version/data_cutoff`，构建器也没有当前权威合同指纹参数；这是当前 5.2 必须补齐的绑定，不能延后，否则无法证明时间截面和合同版本一致。

3. 展示值未绑定 `AtomicFactVersion.raw_value/normalized_value`

- 文件/符号：`pages.py:_assert_record_fact_bound`、`_dossier_efficacy_record`、`_dossier_safety_record`
- 最小构造及实际结果：
  - `fact-region-dup-cn` 保持不变，仅将阶段/状态改为 `I期/进行中`；接受并展示篡改值。
  - `fact-org-origin` 原文为“原研”，组织名改为“伪造企业”；接受。
  - `fact-term-us` 原文为“尚未公开”，到期日改为 `2099-12-31`；接受。
  - `fact-hist-suspend` 原文为“暂停 2023-03-01”，状态日期改为 `2099-12-31`；接受。
  - `fact-v-1` 原文为“52.3 应答率 %”，疗效摘要改为 `999.9 伪造单位`；接受。
  - `fact-v-2` 安全摘要改为 `0.1 伪造安全单位`；接受。
- 预期结果：拒绝，或完全从事实原文/规范化值派生。
- 未捕获原因：现有反例只改 `fact_version_id` 或 locator，没有在 ID、字段、定位均不变时篡改展示值。

4. 公共构建器对 `model_copy/model_construct` 只做部分派生检查

- 文件/符号：`pages.py:_assert_view_inputs_bound`、各 `build_*_view`；`__init__.py` 导出这些构建器。
- 最小构造及实际结果：
  - `AProjectContract.model_copy(update={"eligibility": "excluded"})`：总览接受，仍包含 5 个产品。
  - `ApplicableUniverseSnapshot.model_construct(..., schema_version="9.9")`：竞争格局接受。
  - `GateEvidenceBinding.model_copy(update={"fact_version_id": "fact-not-registered"})`：总览接受；只有产品档案因 `_assert_binding_facts_registered` 才拒绝。
  - `GateEvidenceBinding.model_construct` 构造“未报告但带数值/零分母”的非法绑定：总览接受。
  - `ScientificLineageRegistry.model_copy/model_construct` 篡改事实原文但保留全部 ID：监管视图接受。
- 预期结果：所有公共入口统一重新验证并拒绝伪造对象。
- 未捕获原因：新增测试验证了“不接收 caller analysis”和渲染 DTO 摘要，但没有测试四类输入模型的旁路构造。

5. 完整档案可漏掉 AV06–AV08，也可重复使用同一事实版本

- 文件/符号：`ProductDossier` 默认空集合；`build_product_dossier_view`；`_assert_company_records_closed`、`_assert_patent_records_closed`、`_assert_history_edge_records_closed`
- 最小构造：只传临床记录和监管版本记录，不传企业、专利、历史、邻近观察记录。
- 实际结果：产品档案接受，且 `blocked=False`、疗效/安全摘要存在，但企业、专利、历史均为空。
- 进一步构造同一 `fact-org-origin` 复制为另一企业、同一历史事实改日期复制、同一专利期限事实复制为另一到期日，均接受。
- 预期结果：已有证据事实未被记录时应阻断或显式标记缺失；同一事实版本不得支撑多个冲突记录。
- 未捕获原因：测试只有“全量正向档案”；闭合校验只检查调用方传入的记录，不要求覆盖当前证据，也不按 `fact_version_id` 去重。

6. `EARLY_DECISION` 被无条件映射为“其他适格”

- 文件/符号：`pages.py:_ALLOWED_LAYERS_BY_CONTRACT_ROLE`、`_assert_trial_region_records_closed`
- 最小构造：仅有 `CoreTrialRole.EARLY_DECISION`，没有独立的“其他适格”规则或接受证据，记录标记为 `ClinicalTrialLayer.OTHER_ELIGIBLE`。
- 实际结果：临床组合接受并展示“其他适格”。
- 预期结果：无独立适格规则/证据时应默认排除；不能仅凭 EARLY_DECISION 自动进入。
- 未捕获原因：当前正向夹具本身就是该映射，测试只覆盖未知试验和角色漂移。

7. 监管事件允许不同合同事件复用同一事实版本

- 文件/符号：`pages.py:_assert_versioned_events_closed`
- 最小构造：新增第二个不同 `event_id`、相同类型/地域/日期的合同事件，两个版本记录都引用 `fact-reg`。
- 实际结果：接受并输出两个事件 ID。
- 另将 `fact-reg.raw_value` 改成“已撤回”，仍接受并展示“批准”。
- 预期结果：事件与版本事实一一对应，重复事实或状态冲突失败关闭。
- 未捕获原因：现有测试只覆盖重复同一 `event_id`、错误 event ID 和日期漂移，没有覆盖重复 `fact_version_id` 或事实内容冲突。

P2

8. 用户可见工程词变体仍可泄露

- 文件/符号：`pages.py:_user_facing_text`
- 最小构造及实际结果：`Gate`、`BackendState`、`back-end`、插入零宽字符的 `back​end`、全角 `ｂａｃｋｅｎｄ`、`model-copy` 均接受；精确 `backend-state` 才被拒绝。
- 预期结果：大小写、Unicode、标点拆分和变体均拒绝；合理的 `Dupixent`、`IL-4Rα`、`NCT02407756`、`Novartis` 已实际通过。
- 未捕获原因：测试只覆盖精确 `prompt/backend_enum/下划线`，没有覆盖 Unicode 规范化和变体。

已确认的有效拒绝项：换 `evidence_snapshot_id`、伪造 fact ID、伪造 locator、重复同一监管 `event_id`、监管日期漂移、伪造子集 DTO、档案中的未注册绑定均已失败关闭；这些修复有效，但不足以通过本轮验收。

验证命令与结果：

- `uv run pytest tests/unit/reports/a -q`：110 passed
- `uv run pytest tests/reports/a tests/unit/reports/a -q`：201 passed
- 8 个 AV01–AV08 精确验收节点：各 1 passed
- 目标 Ruff：通过
- strict mypy：通过

所有自建反例使用系统临时目录并自动清理；未修改工作树或报告文件。

最小修复方向：在所有渲染边界拒绝 `analysis.report_ready=False`；通过权威快照存储重新读取并核对锁定内容和合同指纹；统一重验所有输入模型和绑定；建立事实值派生/比较层；按事实版本强制一一对应与完整覆盖；为 `EARLY_DECISION` 增加独立适格证据；对用户文本做 Unicode 规范化和工程词变体拦截。