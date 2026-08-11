继续同一 Phase 2 独立科学数据验收会话。

Hard boundaries:
- Work only inside `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`.
- Read-only review: do not modify any file and do not perform security testing.
- Runner-managed output path: `runs/codex-subagent_ci_phase2_exit_followup.md`. Do not write it with tools; return the complete handoff and let the runner persist it.

Read these files only:
- `src/ci_workflow/sources/receipts.py`
- `src/ci_workflow/sources/retries.py`
- `src/ci_workflow/sources/connectors/authoritative_wechat.py`
- `src/ci_workflow/sources/connectors/china_registries.py`
- `src/ci_workflow/ingestion/locators.py`
- `src/ci_workflow/ingestion/identity.py`
- `src/ci_workflow/domain/evidence.py`
- `src/ci_workflow/capabilities/lineage_registry.py`
- `src/ci_workflow/capabilities/resolution.py`
- `src/ci_workflow/capabilities/ontology_universe.py`
- `migrations/0009_source_date_precision.sql`
- `schemas/source-receipt.schema.json`
- `schemas/source-version.schema.json`
- `tests/unit/test_innovation_eligibility.py`
- `tests/contract/test_evidence_audit_contracts.py`
- `tests/integration/test_competitor_universe.py`
- `tests/integration/test_route_recovery.py`
- `tests/integration/sources/test_authoritative_wechat.py`
- `tests/integration/sources/test_china_routes.py`
- `tests/integration/test_historical_cutoff.py`
- `tests/integration/test_fragment_locators.py`
- `tests/integration/test_source_to_claim_chain.py`
- `fixtures/recorded/phase-2-lineage/nct02912468-minimal.json`
- `package-manifest.json`

保持只读，不修改任何文件，不进行安全测试。

你上一轮结论为 FAIL（P1=9）。父 Codex 已逐项修复，并在可写父环境取得以下机械证据：

- 实施计划正式 Phase 2 套件：59 passed。
- 全库：186 passed。
- Ruff：通过。
- strict mypy：45 个源文件通过。
- 包校验：`PACKAGE_OK version=0.1.0a0 stage=phase-2-review-candidate`。
- `git diff --check`：通过。
- 父会话实时访问 ClinicalTrials.gov 官方 API 成功：NCT02912468，实际入组 276；安慰剂+糠酸莫米松与度普利尤单抗+糠酸莫米松两组；第 24 周鼻塞评分 -0.45（n=133）与 -1.34（n=143）；结果首次发布 2019-07-25；主要论文 PMID 31543428 仍存在。你上一轮代理/DNS失败仅是隔离环境技术限制。

请只读复核当前 diff 和下列实现/测试，重点重新执行上一轮 CE1–CE8 的同类反例：

- `src/ci_workflow/sources/receipts.py`：路线完成必须覆盖全部政策必查单元；最终回执仅可为取得内容或确实未找到；取得内容必须绑定同一 `SourceVersionRecord`。
- `src/ci_workflow/sources/retries.py`：恢复轮次和替代路径必须绑定实际回执；取得内容绑定不可变来源版本；同一路线/实体/缺口/声明域；双轮饱和必须来自实际执行。
- `src/ci_workflow/sources/connectors/authoritative_wechat.py`：产品/试验/事件身份、`mp.weixin.qq.com/s/` 原始链接、已保存正文、摘要与精确定位必须一致。
- `src/ci_workflow/ingestion/locators.py`：直接构造 Registry/Web/PDF 快照也必须校验正文与摘要一致。
- `src/ci_workflow/domain/evidence.py`、`src/ci_workflow/sources/planner.py`、`src/ci_workflow/sources/connectors/china_registries.py`、`migrations/0009_source_date_precision.sql`：首次披露精度与自然日内截止不确定性必须保守处理并持久化。
- `src/ci_workflow/capabilities/lineage_registry.py`、`src/ci_workflow/capabilities/resolution.py`：事实先由重开片段进入科学证据注册表；声明不得引用未注册事实；差异声明须同一试验、不同组别且指标/人群/时间/单位一致。
- `src/ci_workflow/capabilities/ontology_universe.py`、`src/ci_workflow/ingestion/identity.py`：宇宙闭合必须绑定已登记并重开的证据片段。
- `tests/integration/test_source_to_claim_chain.py`：录制 fixture 同时断言 276、两组背景治疗、-0.45/-1.34、133/143、2019-07-25、PMID 31543428；创新药与传统背景治疗的两个身份片段均真实重开；回执/来源版本/缺口/声明同链。

请运行最小决定性检查（禁用 pytest cache，避免只读沙箱噪声）：

`PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -p no:cacheprovider tests/unit/test_innovation_eligibility.py tests/contract/test_evidence_audit_contracts.py tests/integration/test_competitor_universe.py tests/integration/test_route_recovery.py tests/integration/sources/test_authoritative_wechat.py tests/integration/sources/test_china_routes.py tests/integration/test_historical_cutoff.py tests/integration/test_fragment_locators.py tests/integration/test_source_to_claim_chain.py -q`

若发现可执行绕过，给出 P0/P1/P2、最小复现与文件行号；不要因为父会话测试绿色而放行。若原 9 项均闭合且无新 P0/P1，则给出 PASS。明确本结论仍只覆盖 Phase 2 科学数据合同，不覆盖真实全量调研、Phase 3 或报告质量。
