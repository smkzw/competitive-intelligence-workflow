# Task 10.1 实施步骤

- [x] M01：定义 acceptance catalog Schema 与稳定 digest 算法；先写缺字段、非法时区、摘要漂移、绝对路径和额外 case 的 RED。
- [x] M02：建立 `full-matrix-v1` 脱敏输入包，固定特应性皮炎、IANA 时区、物化 cutoff、A+B+C 与 `formats: [html]`。
- [x] M03：建立历史截止正负场景，验证披露/获取时间分离和跨日恢复 cutoff 不漂移。
- [x] M04：建立 `required-v12` 18 个 case 族的目录、输入摘要、预期/禁止不变量、verifier、owner/scope/receipt 合同。
- [x] M05：实现 `tests/acceptance/test_fixture_catalog.py` 的双向闭合与反例测试。
- [x] M06：完成 `docs/acceptance/matrix.md` 中文矩阵，明确首版 HTML-only 与后续四格式恢复边界。
- [x] 独立执行、会商、确定性测试和治理审计通过后收口。

## 精确验收节点

1. `test_full_matrix_scenario_has_indication_timezone_cutoff_hashed_inputs_and_html_only_scope`
2. `test_historical_cutoff_scenario_separates_disclosure_from_acquisition_and_freezes_resume_cutoff`
3. `test_acceptance_catalog_covers_every_required_v12_scenario_with_hashed_inputs`

## 回滚点

发现未脱敏材料、正向模板引用旧失败输出、首版重新要求 PDF/PPT、case/输入摘要不可重算或责任阶段被提前伪造时，撤销本任务新目录并保留 Phase 9 已接受候选包不变。
