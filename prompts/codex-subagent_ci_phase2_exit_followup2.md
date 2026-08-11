继续同一 Phase 2 独立科学数据验收会话 `019ff1d8-8ee4-79e1-b5fe-2aebb063e0be`。

Hard boundaries:
- 只读核验 `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`，不得修改文件，不做安全测试。
- 只复核你上轮报告的 8 个 P1 及其相邻科学合同；不扩大到 Phase 3 或报告质量。
- Runner-managed output path: `runs/codex-subagent_ci_phase2_exit_followup2.md`. Do not write it with tools; return the complete report and let the runner persist it.

Read these files only:
- `src/ci_workflow/sources/receipts.py`
- `src/ci_workflow/sources/planner.py`
- `src/ci_workflow/sources/retries.py`
- `src/ci_workflow/sources/connectors/authoritative_wechat.py`
- `src/ci_workflow/sources/connectors/china_registries.py`
- `src/ci_workflow/domain/evidence.py`
- `src/ci_workflow/domain/claims.py`
- `src/ci_workflow/capabilities/lineage_registry.py`
- `src/ci_workflow/capabilities/resolution.py`
- `src/ci_workflow/capabilities/ontology_universe.py`
- `src/ci_workflow/ingestion/identity.py`
- `schemas/source-version.schema.json`
- `tests/contract/test_evidence_audit_contracts.py`
- `tests/integration/test_route_recovery.py`
- `tests/integration/sources/test_authoritative_wechat.py`
- `tests/integration/sources/test_china_routes.py`
- `tests/integration/test_competitor_universe.py`
- `tests/integration/test_source_to_claim_chain.py`
- `tests/unit/test_innovation_eligibility.py`
- `fixtures/recorded/phase-2-lineage/nct02912468-minimal.json`
- `package-manifest.json`

父 Codex 当前机械证据：
- 正式 Phase 2 套件：60 passed。
- 全库：187 passed。
- Ruff：通过。
- strict mypy：45 个源文件通过。
- 包校验：`PACKAGE_OK version=0.1.0a0 stage=phase-2-review-candidate`。
- `git diff --check`：通过。

重新实际攻击并最小复现：
1. 单次 `not_found` 是否仍能结束；`route_not_applicable`/`route_access_blocked` 是否仍可遗漏政策必查单元；路线尝试是否与来源回执逐条对应。
2. 两轮纯技术错误能否冒充科学穷尽；“未找到”是否必须具备两条实际执行的不同替代路径、连续两轮无新增关键信息，以及恢复策略已写入证据缺口。
3. 取得内容的恢复/替代路线是否必须绑定完整 `SourceVersionRecord`，且内容寻址路径与摘要一致。
4. 公众号是否强制原始微信链接、产品/试验/事件身份、正文摘要、同一定位链接、账号角色和不少于完整短句的正文定位。
5. 中国 CDE/NMPA/药物临床试验登记记录能否使用非官方域名，正文与摘要、稳定标识能否不一致。
6. `ClaimVersion.model_validate()` 无科学证据注册上下文时能否直接接受未注册事实；工厂路径是否仍正常。
7. 竞品宇宙是否仍接受调用方伪造字符串 ID；组件证据和边界审查证据是否都必须来自真实 `ScientificLineageRegistry` 的已重开片段。
8. 录制 NCT02912468 fixture 是否仍贯通官方原文—来源版本—片段—事实—声明，并仅把度普利尤单抗纳入创新药竞品、糠酸莫米松留作背景治疗。

请运行（只读环境使用 `-s -p no:cacheprovider`）：
`PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -s -p no:cacheprovider tests/unit/test_innovation_eligibility.py tests/contract/test_evidence_audit_contracts.py tests/integration/test_competitor_universe.py tests/integration/test_route_recovery.py tests/integration/sources/test_authoritative_wechat.py tests/integration/sources/test_china_routes.py tests/integration/test_historical_cutoff.py tests/integration/test_fragment_locators.py tests/integration/test_source_to_claim_chain.py -q`

输出 `# Phase 2 独立科学数据验收（第二次修复复核）`，给出 PASS/FAIL、P0/P1/P2 数量、执行证据、逐项反例结果、缺陷和进入 Phase 3 前动作。只有 P0/P1=0 才可 PASS；明确 PASS 仅表示 Phase 2 科学数据合同可接受。
