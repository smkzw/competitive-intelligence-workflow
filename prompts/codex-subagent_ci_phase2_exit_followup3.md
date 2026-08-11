继续同一 Phase 2 独立科学数据验收会话 `019ff1d8-8ee4-79e1-b5fe-2aebb063e0be`，只复核你上轮报告的 6 个 P1 修复。

Hard boundaries:
- 只读核验 `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`；不修改文件，不做安全测试，不扩展到 Phase 3。
- Runner-managed output path: `runs/codex-subagent_ci_phase2_exit_followup3.md`. Do not write it with tools; return the complete report and let the runner persist it.

Read these files only:
- `runs/codex-subagent_ci_phase2_exit_followup2.md`
- `src/ci_workflow/sources/receipts.py`
- `src/ci_workflow/sources/planner.py`
- `src/ci_workflow/sources/retries.py`
- `src/ci_workflow/sources/connectors/authoritative_wechat.py`
- `src/ci_workflow/sources/connectors/china_registries.py`
- `src/ci_workflow/storage/content_store.py`
- `src/ci_workflow/capabilities/extraction_normalization.py`
- `src/ci_workflow/capabilities/lineage_registry.py`
- `src/ci_workflow/domain/claims.py`
- `src/ci_workflow/capabilities/resolution.py`
- `tests/contract/test_evidence_audit_contracts.py`
- `tests/integration/test_route_recovery.py`
- `tests/integration/sources/test_authoritative_wechat.py`
- `tests/integration/sources/test_china_routes.py`
- `tests/integration/test_competitor_universe.py`
- `tests/integration/test_source_to_claim_chain.py`
- `tests/unit/test_source_policy.py`

父 Codex 当前机械证据：正式 Phase 2 套件 61 passed；全库 188 passed；Ruff、strict mypy（45 源文件）、包校验和 `git diff --check` 通过。

必须实际重放：
1. 相同回执 ID 但 `result_class`、策略单元、实体、缺口或声明域不同，路线终态是否拒绝。
2. 未完成策略附技术回执、恢复轮次夹带未声明孤立回执、技术回执借无关 `not_found` 单元包装为穷尽证明，是否均拒绝。
3. 公众号短子串是否拒绝；定位是否必须等于已保存正文中的完整非空段落。
4. 中国登记 `calendar_day` 使用 UTC 00:00 而非 `+08:00` 是否拒绝。
5. `ClaimVersion.model_validate(..., context={"accepted_facts": (...)})` 是否拒绝；声明是否只接受受控 `ScientificLineageRegistry`，且事实只能通过候选事实接受流程进入注册表。
6. 直接构造 `VerifiedEvidenceFragment`/`ScientificLineageRegistry` 是否拒绝；正式路径是否必须从 SQLite 真源库重读片段、来源版本与内容寻址正文，并拒绝不存在于正文的伪片段。

运行：
`PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -s -p no:cacheprovider tests/unit/test_innovation_eligibility.py tests/unit/test_source_policy.py tests/contract/test_evidence_audit_contracts.py tests/integration/test_competitor_universe.py tests/integration/test_route_recovery.py tests/integration/sources/test_authoritative_wechat.py tests/integration/sources/test_china_routes.py tests/integration/test_source_to_claim_chain.py -q`

输出 `# Phase 2 独立科学数据验收（最终窄复核）`，结论 PASS/FAIL、P0/P1/P2、执行证据、六项反例结果及 Phase 3 边界。只有 P0/P1=0 才可 PASS。
